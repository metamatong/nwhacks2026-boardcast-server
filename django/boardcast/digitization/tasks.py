import logging
from pathlib import Path
from typing import Any, List

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from .constants import (
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
    STAGE_ALIGNMENT,
    STAGE_BACKGROUND,
    STAGE_DONE,
    STAGE_INK,
    STAGE_LOADING,
    STAGE_RENDER,
    STAGE_SAVING,
    STAGE_STROKE,
    STAGE_WHITEBOARD_DETECTION,
)
from .models import DigitizationFrame, DigitizationJob
logger = logging.getLogger(__name__)


def _load_frames(frames: List[DigitizationFrame]) -> List[Any]:
    import cv2
    import numpy as np

    images = []
    for frame in frames:
        with frame.image.open("rb") as fh:
            data = fh.read()
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Failed to decode frame {frame.id}")
        images.append(img)
    return images


@shared_task
def process_digitization_job(job_id: str) -> None:
    try:
        job = DigitizationJob.objects.get(id=job_id)
    except DigitizationJob.DoesNotExist:
        logger.warning("DigitizationJob %s not found", job_id)
        return

    if job.status not in {STATUS_QUEUED, STATUS_RUNNING}:
        logger.info("DigitizationJob %s not queued/running (status=%s)", job_id, job.status)
        return

    job.status = STATUS_RUNNING
    job.stage = STAGE_LOADING
    job.processed_frames = 0
    job.error_code = ""
    job.error_message = ""
    job.started_at = timezone.now()
    job.save()

    try:
        import numpy as np
        import cv2

        from .pipeline import (
            align_image,
            build_config,
            detect_ink_mask,
            detect_person_mask,
            detect_whiteboard_bbox,
            encode_image,
            estimate_background,
            estimate_stroke_colors,
            get_yolo_model,
            render_canvas,
        )

        frames_qs = list(DigitizationFrame.objects.filter(job=job).order_by("frame_index"))
        if not frames_qs:
            raise ValueError("No frames uploaded")

        config = build_config(job.options)
        images = _load_frames(frames_qs)

        job.stage = STAGE_WHITEBOARD_DETECTION
        job.save(update_fields=["stage"])

        x, y, bw, bh = detect_whiteboard_bbox(images[0], config)
        images = [img[y:y + bh, x:x + bw] for img in images]

        h, w = images[0].shape[:2]
        total_frames = len(images)

        orb = cv2.ORB_create(int(config["orb_features"]))
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        ref = images[0]
        ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
        ref_kp, ref_des = orb.detectAndCompute(ref_gray, None)

        stack = np.zeros((total_frames, h, w, 3), dtype=np.uint8)
        person_mask_stack = np.zeros((total_frames, h, w), dtype=bool)
        bg_mask_stack = np.ones((total_frames, h, w), dtype=bool)

        model_path = Path(settings.DIGITIZATION_MODEL_PATH)
        if not model_path.exists():
            raise ValueError(f"YOLO model not found at {model_path}")
        model = get_yolo_model(str(model_path))

        job.stage = STAGE_ALIGNMENT
        job.save(update_fields=["stage"])

        excluded_frames = 0
        for i, img in enumerate(images):
            aligned = align_image(img, ref_kp, ref_des, orb, bf, (w, h), config)
            stack[i] = aligned

            person_mask = detect_person_mask(aligned, model, (h, w), config)

            if config.get("expect_person_in_each_frame"):
                min_area = int(float(config["min_person_area_ratio"]) * person_mask.size)
                if person_mask.sum() < min_area:
                    bg_mask_stack[i] = False
                    person_mask_stack[i] = True
                    excluded_frames += 1
                    job.processed_frames = i + 1
                    job.save(update_fields=["processed_frames"])
                    continue

            person_mask_stack[i] = person_mask
            bg_mask_stack[i] = ~person_mask
            job.processed_frames = i + 1
            job.save(update_fields=["processed_frames"])

        frames_used = int((bg_mask_stack.reshape(total_frames, -1).any(axis=1)).sum())
        if frames_used == 0:
            raise ValueError("No usable frames after person detection")

        job.stage = STAGE_BACKGROUND
        job.save(update_fields=["stage"])
        background = estimate_background(stack, bg_mask_stack)

        job.stage = STAGE_INK
        job.save(update_fields=["stage"])
        ink_mask = detect_ink_mask(background, config)

        job.stage = STAGE_STROKE
        job.save(update_fields=["stage"])
        stroke_color = estimate_stroke_colors(stack, ink_mask, person_mask_stack)

        job.stage = STAGE_RENDER
        job.save(update_fields=["stage"])
        canvas = render_canvas(background, ink_mask, stroke_color)

        debug_img = np.hstack([background, canvas])

        job.stage = STAGE_SAVING
        job.save(update_fields=["stage"])

        background_bytes = encode_image(background, ".jpg")
        canvas_bytes = encode_image(canvas, ".png")
        debug_bytes = encode_image(debug_img, ".jpg")

        job.background_image.save("background.jpg", ContentFile(background_bytes), save=False)
        job.result_image.save("digital_board.png", ContentFile(canvas_bytes), save=False)
        job.debug_image.save("comparison.jpg", ContentFile(debug_bytes), save=False)

        ink_pct = float(ink_mask.sum()) / float(ink_mask.size) * 100.0

        job.metrics = {
            "ink_coverage_pct": round(ink_pct, 4),
            "excluded_frames": excluded_frames,
            "frames_used": frames_used,
            "total_frames": total_frames,
        }
        job.status = STATUS_SUCCEEDED
        job.stage = STAGE_DONE
        job.finished_at = timezone.now()
        job.save()

    except Exception as exc:
        logger.exception("DigitizationJob %s failed", job_id)
        job.status = STATUS_FAILED
        job.error_message = str(exc)
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_message", "finished_at"])
