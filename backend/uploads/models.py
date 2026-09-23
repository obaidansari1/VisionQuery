from django.db import models
from pgvector.django import HnswIndex, VectorField


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


class Frame(models.Model):
    """A sampled frame from a video, stored with a CLIP embedding for semantic search."""

    class SampleType(models.TextChoices):
        FIXED = "fixed", "Fixed"
        ACTIVE = "active", "Active"

    video = models.ForeignKey(VideoUpload, related_name="frames", on_delete=models.CASCADE)
    frame_number = models.IntegerField()
    timestamp_seconds = models.FloatField()
    sample_type = models.CharField(max_length=16, choices=SampleType.choices)
    image = models.ImageField(upload_to="frame_thumbnails/%Y/%m/%d/")
    # CLIP ViT-B/32 produces 512-dim embeddings; image and text share the same space,
    # so a text query embedding can be compared directly against frame embeddings.
    embedding = VectorField(dimensions=512, null=True, blank=True)

    class Meta:
        ordering = ["timestamp_seconds"]
        indexes = [
            HnswIndex(
                name="frame_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self):
        return f"Frame {self.frame_number} of video {self.video_id} ({self.sample_type})"
