from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from pgvector.django import CosineDistance
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .clip_model import get_embedder
from .models import Frame, VideoUpload
from .serializers import (
    FrameResultSerializer,
    VideoListSerializer,
    VideoSearchSerializer,
    VideoUploadCreateSerializer,
    VideoUploadStatusSerializer,
)
from .tasks import process_video_upload


class IndexView(TemplateView):
    """Serves the single-page demo UI (upload, status, search) from the same origin as the API."""

    template_name = "index.html"


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
        data = VideoUploadStatusSerializer(video_upload, context={"request": request}).data
        return Response(data)


class VideoListView(ListAPIView):
    """Lists uploaded videos, most recent first, for the demo UI's video picker."""

    serializer_class = VideoListSerializer

    def get_queryset(self):
        return VideoUpload.objects.all().order_by("-uploaded_at").annotate(
            frame_count=Count("frames")
        )

    def get_serializer_context(self):
        return {"request": self.request}


class VideoSearchView(APIView):
    """Semantic search: embeds the text query with CLIP and ranks stored frames by cosine similarity."""

    def post(self, request):
        serializer = VideoSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data["query"]
        video_id = serializer.validated_data.get("video_id")
        top_k = serializer.validated_data["top_k"]

        if video_id is not None:
            get_object_or_404(VideoUpload, pk=video_id)

        embedder = get_embedder()
        query_embedding = embedder.embed_text(query)

        frames = Frame.objects.filter(embedding__isnull=False)
        if video_id is not None:
            frames = frames.filter(video_id=video_id)

        results = frames.annotate(distance=CosineDistance("embedding", query_embedding)).order_by(
            "distance"
        )[:top_k]

        data = FrameResultSerializer(results, many=True, context={"request": request}).data
        return Response({"query": query, "video_id": video_id, "results": data})
