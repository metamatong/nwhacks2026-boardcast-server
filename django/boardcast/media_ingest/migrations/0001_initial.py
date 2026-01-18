import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AudioChunk",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("room_id", models.UUIDField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("file", models.FileField(upload_to="audio_chunks/")),
                ("duration_ms", models.IntegerField(default=0)),
            ],
        ),
    ]
