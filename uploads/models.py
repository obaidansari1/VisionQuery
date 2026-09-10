from django.db import models


class VideoUpload(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    file = models.FileField(upload_to="video_uploads/%Y/%m/%d/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)

    def __str__(self):
        return f"Video upload {self.pk} ({self.status})"
