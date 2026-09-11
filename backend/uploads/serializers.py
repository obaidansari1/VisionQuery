from rest_framework import serializers

from .models import VideoUpload


class VideoUploadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoUpload
        fields = ("file",)


class VideoUploadStatusSerializer(serializers.ModelSerializer):
    video_id = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = VideoUpload
        fields = ("video_id", "status", "uploaded_at")
