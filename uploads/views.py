from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import VideoUpload
from .serializers import VideoUploadCreateSerializer, VideoUploadStatusSerializer
from .tasks import process_video_upload


class VideoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        serializer = VideoUploadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video_upload = serializer.save(status=VideoUpload.Status.PENDING)

        # Queue only after the database write is committed, so workers can read it.
        transaction.on_commit(lambda: process_video_upload.delay(video_upload.id))

        return Response({"video_id": video_upload.id}, status=status.HTTP_201_CREATED)


class VideoUploadStatusView(APIView):
    def get(self, request, video_id):
        video_upload = get_object_or_404(VideoUpload, pk=video_id)
        return Response(VideoUploadStatusSerializer(video_upload).data)
