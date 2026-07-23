"""Safe Pillow-to-ONNX preprocessing for RGB furniture images."""

from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

MODEL_INPUT_SIZE = (224, 224)
MAX_DECODED_PIXELS = 25_000_000
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class InvalidClassifierImageError(ValueError):
    """The stored upload cannot safely be decoded as an image."""


def preprocess_image(image_path: Path) -> Any:
    """Decode, orient, crop, normalize, and return a 1x3x224x224 float tensor."""
    try:
        import numpy as np
    except ImportError as error:
        raise RuntimeError("The configured classifier numerical runtime is unavailable.") from error
    try:
        with Image.open(image_path) as source:
            width, height = source.size
            if width <= 0 or height <= 0 or width * height > MAX_DECODED_PIXELS:
                raise InvalidClassifierImageError(
                    "The decoded image dimensions exceed the classifier safety limit."
                )
            source.load()
            oriented = ImageOps.exif_transpose(source)
            rgb = oriented.convert("RGB")
            resized = ImageOps.fit(
                rgb,
                MODEL_INPUT_SIZE,
                method=Image.Resampling.BILINEAR,
                centering=(0.5, 0.5),
            )
            pixels = np.asarray(resized, dtype=np.float32) / 255.0
    except InvalidClassifierImageError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise InvalidClassifierImageError(
            "The uploaded image is corrupted, unreadable, or not a supported image."
        ) from error

    mean = np.asarray(IMAGENET_MEAN, dtype=np.float32)
    standard_deviation = np.asarray(IMAGENET_STD, dtype=np.float32)
    normalized = (pixels - mean) / standard_deviation
    return np.transpose(normalized, (2, 0, 1))[np.newaxis, ...].astype(np.float32)
