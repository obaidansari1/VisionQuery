from django.urls import path

from .views import (
    VideoListView,
    VideoSearchView,
    VideoUploadStatusView,
    VideoUploadView,
)

urlpatterns = [
    path("upload/", VideoUploadView.as_view(), name="video-upload"),
    path("status/<int:video_id>/", VideoUploadStatusView.as_view(), name="video-status"),
    path("videos/", VideoListView.as_view(), name="video-list"),
    path("search/", VideoSearchView.as_view(), name="video-search"),
]
