import django.db.models.deletion
import pgvector.django
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("uploads", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Frame",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("frame_number", models.IntegerField()),
                ("timestamp_seconds", models.FloatField()),
                (
                    "sample_type",
                    models.CharField(
                        choices=[("fixed", "Fixed"), ("active", "Active")], max_length=16
                    ),
                ),
                ("image", models.ImageField(upload_to="frame_thumbnails/%Y/%m/%d/")),
                (
                    "embedding",
                    pgvector.django.VectorField(blank=True, dimensions=512, null=True),
                ),
                (
                    "video",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="frames",
                        to="uploads.videoupload",
                    ),
                ),
            ],
            options={
                "ordering": ["timestamp_seconds"],
            },
        ),
        migrations.AddIndex(
            model_name="frame",
            index=pgvector.django.HnswIndex(
                name="frame_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ),
    ]
