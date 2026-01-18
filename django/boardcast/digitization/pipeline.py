import warnings
from functools import lru_cache
from typing import Dict, Tuple

import cv2
import numpy as np
from ultralytics import YOLO

DEFAULT_CONFIG: Dict[str, object] = {
    "conf": 0.4,
    "person_class": 0,
    "whiteboard_thresh": 200,
    "min_whiteboard_area": 10000,
    "orb_features": 1000,
    "min_match_count": 10,
    "ransac_threshold": 5.0,
    "adaptive_block_size": 31,
    "adaptive_c": 5,
    "morph_kernel_size": 3,
    "expect_person_in_each_frame": True,
    "min_person_area_ratio": 0.003,
}


def build_config(options: Dict[str, object]) -> Dict[str, object]:
    config = DEFAULT_CONFIG.copy()
    for key, value in (options or {}).items():
        if key in config:
            config[key] = value

    block_size = int(config["adaptive_block_size"])
    if block_size % 2 == 0:
        block_size += 1
    config["adaptive_block_size"] = max(3, block_size)

    return config


@lru_cache(maxsize=1)
def get_yolo_model(model_path: str) -> YOLO:
    return YOLO(model_path)


def detect_whiteboard_bbox(img: np.ndarray, config: Dict[str, object]) -> Tuple[int, int, int, int]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)

    _, thresh = cv2.threshold(
        gray,
        int(config["whiteboard_thresh"]),
        255,
        cv2.THRESH_BINARY,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No whiteboard detected in the first frame")

    min_area = int(config["min_whiteboard_area"])
    valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]
    if not valid_contours:
        raise ValueError(f"No contours larger than {min_area} pixels found")

    largest_contour = max(valid_contours, key=cv2.contourArea)
    return cv2.boundingRect(largest_contour)


def align_image(
    img: np.ndarray,
    ref_kp,
    ref_des,
    orb,
    bf,
    target_size: Tuple[int, int],
    config: Dict[str, object],
) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kp, des = orb.detectAndCompute(gray, None)

    if des is None or ref_des is None or len(kp) < 4:
        return img

    matches = bf.match(ref_des, des)
    matches = sorted(matches, key=lambda x: x.distance)[:50]

    if len(matches) < int(config["min_match_count"]):
        return img

    src_pts = np.float32([ref_kp[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

    H, _ = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, float(config["ransac_threshold"]))
    if H is None:
        return img

    w, h = target_size
    return cv2.warpPerspective(img, H, (w, h), flags=cv2.INTER_LINEAR)


def detect_person_mask(
    img: np.ndarray,
    model: YOLO,
    target_size: Tuple[int, int],
    config: Dict[str, object],
) -> np.ndarray:
    h, w = target_size
    person_mask = np.zeros((h, w), dtype=bool)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = model(img, conf=float(config["conf"]), verbose=False)

    for r in results:
        if not hasattr(r, "masks") or r.masks is None:
            continue
        for j, seg in enumerate(r.masks.data):
            cls = int(r.boxes.cls[j])
            if cls != int(config["person_class"]):
                continue
            seg_np = cv2.resize(seg.cpu().numpy(), (w, h), interpolation=cv2.INTER_LINEAR)
            person_mask |= (seg_np > 0.5)

    if person_mask.any():
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        person_mask = cv2.morphologyEx(person_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel).astype(bool)

    return person_mask


def estimate_background(stack: np.ndarray, bg_mask_stack: np.ndarray) -> np.ndarray:
    masked_bg = np.where(bg_mask_stack[..., None], stack.astype(np.float32), np.nan)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        background = np.nanmedian(masked_bg, axis=0)

    nan_mask = np.isnan(background[..., 0])
    background = np.nan_to_num(background, nan=255).astype(np.uint8)

    if nan_mask.any():
        background = cv2.inpaint(background, nan_mask.astype(np.uint8), 3, cv2.INPAINT_TELEA)

    return background


def detect_ink_mask(background: np.ndarray, config: Dict[str, object]) -> np.ndarray:
    gray_bg = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
    gray_bg = cv2.bilateralFilter(gray_bg, 5, 50, 50)

    ink_mask = cv2.adaptiveThreshold(
        gray_bg,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        int(config["adaptive_block_size"]),
        int(config["adaptive_c"]),
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (int(config["morph_kernel_size"]), int(config["morph_kernel_size"])),
    )
    ink_mask = cv2.morphologyEx(ink_mask, cv2.MORPH_OPEN, kernel)

    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    ink_mask = cv2.morphologyEx(ink_mask, cv2.MORPH_CLOSE, kernel_close)

    return ink_mask.astype(bool)


def estimate_stroke_colors(
    stack: np.ndarray,
    ink_mask: np.ndarray,
    person_mask_stack: np.ndarray,
) -> np.ndarray:
    stroke_mask = ink_mask[None, ...] & (~person_mask_stack)
    stroke_mask_rgb = np.repeat(stroke_mask[..., None], 3, axis=3)
    stroke_stack = np.where(stroke_mask_rgb, stack.astype(np.float32), np.nan)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stroke_color = np.nanmedian(stroke_stack, axis=0)

    stroke_color = np.where(np.isnan(stroke_color), 255, stroke_color).astype(np.uint8)

    return stroke_color


def render_canvas(background: np.ndarray, ink_mask: np.ndarray, stroke_color: np.ndarray) -> np.ndarray:
    canvas = np.ones_like(background) * 255
    canvas[ink_mask] = stroke_color[ink_mask]
    return canvas


def encode_image(image: np.ndarray, ext: str, params=None) -> bytes:
    success, buffer = cv2.imencode(ext, image, params or [])
    if not success:
        raise ValueError("Failed to encode image")
    return buffer.tobytes()
