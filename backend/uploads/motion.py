"""Lightweight frame-difference motion detection for video processing."""

import cv2


class MotionDetector:
    """Detect visible changes between consecutive low-resolution grayscale frames."""

    def __init__(self, threshold: float, resize_width: int = 320) -> None:
        self.threshold = threshold
        self.resize_width = resize_width
        self.previous_frame = None

    def preprocess_frame(self, frame):
        """Resize, grayscale, and blur a frame before comparing it."""
        height, width = frame.shape[:2]
        resized_height = max(1, round(height * self.resize_width / width))
        resized = cv2.resize(frame, (self.resize_width, resized_height))
        grayscale = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(grayscale, (5, 5), 0)

    def calculate_motion_score(self, current_frame, previous_frame) -> float:
        """Return the percentage of pixels that changed noticeably."""
        difference = cv2.absdiff(current_frame, previous_frame)
        _, changed_pixels = cv2.threshold(difference, 25, 255, cv2.THRESH_BINARY)
        return 100 * cv2.countNonZero(changed_pixels) / changed_pixels.size

    def is_motion_detected(self, score: float) -> bool:
        """Determine whether a difference score is meaningful motion."""
        return score >= self.threshold

    def check_frame(self, frame) -> tuple[bool, float]:
        """Compare a frame with the previous motion-check frame."""
        current_frame = self.preprocess_frame(frame)
        if self.previous_frame is None:
            self.previous_frame = current_frame
            return False, 0.0

        score = self.calculate_motion_score(current_frame, self.previous_frame)
        self.previous_frame = current_frame
        return self.is_motion_detected(score), score
