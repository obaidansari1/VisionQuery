from rest_framework import serializers

from .models import Frame, VideoUpload


class VideoUploadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoUpload
        fields = ("file",)


class VideoUploadStatusSerializer(serializers.ModelSerializer):
    video_id = serializers.IntegerField(source="id", read_only=True)
    file_url = serializers.SerializerMethodField()
    frame_count = serializers.SerializerMethodField()

    class Meta:
        model = VideoUpload
        fields = ("video_id", "status", "uploaded_at", "file_url", "frame_count")

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url

    def get_frame_count(self, obj):
        return obj.frames.count()


class VideoListSerializer(serializers.ModelSerializer):
    video_id = serializers.IntegerField(source="id", read_only=True)
    file_url = serializers.SerializerMethodField()
    frame_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VideoUpload
        fields = ("video_id", "status", "uploaded_at", "file_url", "frame_count")

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


class VideoSearchSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500, trim_whitespace=True)
    video_id = serializers.IntegerField(required=False, allow_null=True)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=50, default=8)

    def validate_query(self, value):
        if not value.strip():
            raise serializers.ValidationError("query must not be empty")
        return value


class FrameResultSerializer(serializers.ModelSerializer):
    video_id = serializers.IntegerField(read_only=True)
    image_url = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()

    class Meta:
        model = Frame
        fields = (
            "video_id",
            "frame_number",
            "timestamp_seconds",
            "sample_type",
            "image_url",
            "score",
        )

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url

    def get_score(self, obj):
        # `distance` is added by the queryset's CosineDistance annotation in the search view.
        distance = getattr(obj, "distance", None)
        if distance is None:
            return None
        return round(1 - distance, 4)
