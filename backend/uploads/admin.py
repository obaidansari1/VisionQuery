from django.contrib import admin
from django.utils.html import format_html

from .models import Frame, VideoUpload


class FrameInline(admin.TabularInline):
    model = Frame
    extra = 0
    fields = ("thumbnail", "frame_number", "timestamp_seconds", "sample_type")
    readonly_fields = ("thumbnail", "frame_number", "timestamp_seconds", "sample_type")
    can_delete = False

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:60px;border-radius:4px;" />', obj.image.url)
        return "—"


@admin.register(VideoUpload)
class VideoUploadAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "uploaded_at", "frame_count")
    readonly_fields = ("uploaded_at",)
    inlines = [FrameInline]

    def frame_count(self, obj):
        return obj.frames.count()


@admin.register(Frame)
class FrameAdmin(admin.ModelAdmin):
    list_display = ("id", "video", "thumbnail", "frame_number", "timestamp_seconds", "sample_type")
    list_filter = ("sample_type", "video")

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:60px;border-radius:4px;" />', obj.image.url)
        return "—"
