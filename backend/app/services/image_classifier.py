"""Replaceable furniture classifier interface and development implementation.

The current classifier is a deterministic placeholder based on file content. It
does not represent trained-model accuracy and must be replaced for production AI.
"""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from PIL import Image, UnidentifiedImageError

SUPPORTED_CLASSES = ("chair", "bed", "sofa", "dining_table", "lamp_shade")
DISPLAY_NAMES = {
    "chair": "Chair",
    "bed": "Bed",
    "sofa": "Sofa",
    "dining_table": "Dining Table",
    "lamp_shade": "Lamp Shade",
}


class UnreadableImageError(ValueError):
    """Raised when Pillow cannot fully decode an uploaded image."""


@dataclass(frozen=True)
class ClassifierResult:
    predicted_class: str
    display_name: str
    confidence: float
    model_name: str = "wue-development-classifier"
    model_version: str = "0.1.0"
    is_placeholder: bool = True


class DevelopmentImageClassifier:
    """Deterministic placeholder satisfying the future classifier boundary."""

    def classify_image(self, image_path: Path) -> ClassifierResult:
        try:
            with Image.open(image_path) as image:
                image.verify()
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
            raise UnreadableImageError("The uploaded image is corrupted or unreadable.") from error

        digest = sha256(image_path.read_bytes()).digest()
        predicted_class = SUPPORTED_CLASSES[int.from_bytes(digest[:2], "big") % len(SUPPORTED_CLASSES)]
        confidence = round(0.55 + (int.from_bytes(digest[2:4], "big") % 3500) / 10_000, 4)
        return ClassifierResult(
            predicted_class=predicted_class,
            display_name=DISPLAY_NAMES[predicted_class],
            confidence=confidence,
        )


image_classifier = DevelopmentImageClassifier()
