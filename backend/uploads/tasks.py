import io
import logging
from collections import deque

import cv2
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image

from .clip_model import get_embedder
from .models import Frame, VideoUpload
from .motion import MotionDetector

logger = logging.getLogger(__name__)

# This setting can be overridden with VIDEO_SAMPLING_TARGET_FPS in settings.py.
TARGET_FPS = settings.VIDEO_SAMPLING_TARGET_FPS
MOTION_CHECK_FPS = settings.VIDEO_MOTION_CHECK_FPS
MOTION_THRESHOLD = settings.VIDEO_MOTION_THRESHOLD
ACTIVE_SAMPLING_FPS = settings.VIDEO_ACTIVE_SAMPLING_FPS
ACTIVE_WINDOW_SECONDS = settings.VIDEO_ACTIVE_WINDOW_SECONDS
PRE_ROLL_SECONDS = settings.VIDEO_PRE_ROLL_SECONDS
MOTION_RESIZE_WIDTH = settings.VIDEO_MOTION_RESIZE_WIDTH
ADAPTIVE_SAMPLING_DEBUG = settings.VIDEO_ADAPTIVE_SAMPLING_DEBUG

JPEG_QUALITY = 85


def save_sampled_frame(
    video_upload: VideoUpload,
    frame_number: int,
    timestamp_seconds: float,
    sample_type: str,
    frame_bgr,
    embedder,
):
    """Encode a frame as JPEG, embed it with CLIP, and persist it as a searchable Frame."""
    success, buffer = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    if not success:
        logger.warning(
            "Could not encode frame video_id=%s frame=%s", video_upload.id, frame_number
        )
        return None

    image_bytes = buffer.tobytes()
    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    embedding = embedder.embed_image(pil_image)

    frame = Frame(
        video=video_upload,
        frame_number=frame_number,
        timestamp_seconds=timestamp_seconds,
        sample_type=sample_type,
        embedding=embedding,
    )
    frame.image.save(
        f"video{video_upload.id}_frame{frame_number}.jpg",
        ContentFile(image_bytes),
        save=False,
    )
    frame.save()
    return frame


@shared_task
def process_video_upload(video_id: int) -> None:
    """Sample fixed + motion-triggered frames, embed each with CLIP, and store them for search."""
    video_upload = None
    capture = None

    try:
        video_upload = VideoUpload.objects.get(pk=video_id)
        video_upload.status = VideoUpload.Status.PROCESSING
        video_upload.save(update_fields=["status"])
        logger.info("Started video upload processing: video_id=%s", video_id)

        if (
            TARGET_FPS <= 0
            or MOTION_CHECK_FPS <= 0
            or ACTIVE_SAMPLING_FPS <= 0
            or ACTIVE_WINDOW_SECONDS <= 0
            or PRE_ROLL_SECONDS < 0
            or MOTION_RESIZE_WIDTH <= 0
        ):
            raise ValueError("Video sampling and motion-detection settings must be valid")

        capture = cv2.VideoCapture(video_upload.file.path)
        if not capture.isOpened():
            raise ValueError("OpenCV could not open the uploaded video")

        source_fps = capture.get(cv2.CAP_PROP_FPS)
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if source_fps <= 0 or total_frames <= 0:
            raise ValueError(
                "Video has invalid metadata: "
                f"fps={source_fps}, total_frames={total_frames}"
            )

        duration_seconds = total_frames / source_fps
        frame_interval = max(1, round(source_fps / TARGET_FPS))
        logger.info(
            "Video metadata: video_id=%s fps=%.2f total_frames=%s duration=%.2fs "
            "fixed_target_fps=%s fixed_frame_interval=%s",
            video_id,
            source_fps,
            total_frames,
            duration_seconds,
            TARGET_FPS,
            frame_interval,
        )
        logger.info(
            "Adaptive sampling settings: video_id=%s motion_check_fps=%s "
            "motion_threshold=%.2f%% active_sampling_fps=%s "
            "active_window_seconds=%s pre_roll_seconds=%s",
            video_id,
            MOTION_CHECK_FPS,
            MOTION_THRESHOLD,
            ACTIVE_SAMPLING_FPS,
            ACTIVE_WINDOW_SECONDS,
            PRE_ROLL_SECONDS,
        )

        embedder = get_embedder()

        frame_number = 0
        fixed_sampled_frames = 0
        active_sampled_frames = 0
        saved_frames = 0
        saved_frame_numbers = set()
        motion_detector = MotionDetector(MOTION_THRESHOLD, MOTION_RESIZE_WIDTH)
        motion_check_interval = 1 / MOTION_CHECK_FPS
        active_sample_interval = 1 / ACTIVE_SAMPLING_FPS
        next_motion_check_timestamp = 0.0
        active_window_end = None
        next_active_sample_timestamp = None
        # Pre-roll buffer keeps recent frame images too, so that when motion is first
        # detected we can back-fill Frame rows for the moments just before it started.
        pre_roll_frames = deque()

        active_windows = 0

        def store(frame_number_, timestamp_, sample_type_, frame_bgr_):
            nonlocal saved_frames
            if frame_number_ in saved_frame_numbers:
                return
            saved_frame_numbers.add(frame_number_)
            frame = save_sampled_frame(
                video_upload, frame_number_, timestamp_, sample_type_, frame_bgr_, embedder
            )
            if frame is not None:
                saved_frames += 1

        while True:
            success, frame = capture.read()
            if not success:
                break

            timestamp_seconds = frame_number / source_fps

            if frame_number % frame_interval == 0:
                fixed_sampled_frames += 1
                store(frame_number, timestamp_seconds, Frame.SampleType.FIXED, frame)
                if ADAPTIVE_SAMPLING_DEBUG:
                    logger.info(
                        "Fixed sampled video_id=%s frame=%s timestamp=%.2fs",
                        video_id,
                        frame_number,
                        timestamp_seconds,
                    )
                else:
                    logger.debug(
                        "Fixed sampled video_id=%s frame=%s timestamp=%.2fs",
                        video_id,
                        frame_number,
                        timestamp_seconds,
                    )

            pre_roll_frames.append((frame_number, timestamp_seconds, frame.copy()))
            pre_roll_start = timestamp_seconds - PRE_ROLL_SECONDS
            while pre_roll_frames and pre_roll_frames[0][1] < pre_roll_start:
                pre_roll_frames.popleft()

            if timestamp_seconds >= next_motion_check_timestamp:
                motion_detected, motion_score = motion_detector.check_frame(frame)
                next_motion_check_timestamp = timestamp_seconds + motion_check_interval

                if ADAPTIVE_SAMPLING_DEBUG:
                    logger.info(
                        "Motion check video_id=%s timestamp=%.2fs score=%.2f%%",
                        video_id,
                        timestamp_seconds,
                        motion_score,
                    )

                if motion_detected:
                    window_end = timestamp_seconds + ACTIVE_WINDOW_SECONDS
                    if active_window_end is None or timestamp_seconds > active_window_end:
                        window_start = max(0.0, timestamp_seconds - PRE_ROLL_SECONDS)
                        active_window_end = window_end
                        next_active_sample_timestamp = window_start
                        active_windows += 1
                        logger.info(
                            "Motion detected: video_id=%s timestamp=%.2fs score=%.2f%% "
                            "active_window=%.2fs-%.2fs",
                            video_id,
                            timestamp_seconds,
                            motion_score,
                            window_start,
                            active_window_end,
                        )

                        for buffered_frame, buffered_timestamp, buffered_image in pre_roll_frames:
                            if buffered_timestamp >= next_active_sample_timestamp:
                                store(
                                    buffered_frame,
                                    buffered_timestamp,
                                    Frame.SampleType.ACTIVE,
                                    buffered_image,
                                )
                                active_sampled_frames += 1
                                next_active_sample_timestamp += active_sample_interval
                    else:
                        previous_window_end = active_window_end
                        active_window_end = max(active_window_end, window_end)
                        if (
                            ADAPTIVE_SAMPLING_DEBUG
                            and active_window_end > previous_window_end
                        ):
                            logger.info(
                                "Active window extended: video_id=%s end=%.2fs",
                                video_id,
                                active_window_end,
                            )

            if active_window_end is not None:
                if timestamp_seconds <= active_window_end:
                    if timestamp_seconds >= next_active_sample_timestamp:
                        store(frame_number, timestamp_seconds, Frame.SampleType.ACTIVE, frame)
                        active_sampled_frames += 1
                        next_active_sample_timestamp += active_sample_interval
                else:
                    logger.info(
                        "Active window finished: video_id=%s timestamp=%.2fs",
                        video_id,
                        active_window_end,
                    )
                    active_window_end = None
                    next_active_sample_timestamp = None

            frame_number += 1

        if active_window_end is not None:
            logger.info(
                "Active window finished: video_id=%s timestamp=%.2fs",
                video_id,
                min(active_window_end, duration_seconds),
            )

        video_upload.status = VideoUpload.Status.DONE
        video_upload.save(update_fields=["status"])
        logger.info(
            "Finished video upload processing: video_id=%s fixed_sampled_frames=%s "
            "active_windows=%s active_sampled_frames=%s frames_saved=%s",
            video_id,
            fixed_sampled_frames,
            active_windows,
            active_sampled_frames,
            saved_frames,
        )
    except VideoUpload.DoesNotExist:
        logger.error("Video upload was not found: video_id=%s", video_id)
    except ValueError as error:
        logger.error("Video upload failed: video_id=%s error=%s", video_id, error)
        if video_upload is not None:
            video_upload.status = VideoUpload.Status.FAILED
            video_upload.save(update_fields=["status"])
    except Exception:
        logger.exception("Unexpected video processing error: video_id=%s", video_id)
        if video_upload is not None:
            video_upload.status = VideoUpload.Status.FAILED
            video_upload.save(update_fields=["status"])
        raise
    finally:
        if capture is not None:
            capture.release()
