import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Room",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("title", models.CharField(max_length=200, blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("join_code", models.CharField(max_length=32, blank=True, default="")),
                ("janus_room_id", models.BigIntegerField(blank=True, null=True)),
            ],
        ),
    ]
