from django.urls import path

from .views import VideoUploadStatusView, VideoUploadView

urlpatterns = [
    path("upload/", VideoUploadView.as_view(), name="video-upload"),
    path("status/<int:video_id>/", VideoUploadStatusView.as_view(), name="video-status"),
]
