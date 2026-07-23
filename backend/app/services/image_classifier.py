"""Backward-compatible imports for the Phase 8.2 classifier adapter."""

from app.ai.classifier import (
    ClassifierUnavailableError,
    FurnitureClassifier,
    InvalidClassifierImageError,
    ModelOutputError,
    furniture_classifier as image_classifier,
)
from app.ai.labels import DISPLAY_NAMES, SUPPORTED_LABELS

SUPPORTED_CLASSES = SUPPORTED_LABELS
UnreadableImageError = InvalidClassifierImageError

__all__ = [
    "ClassifierUnavailableError",
    "DISPLAY_NAMES",
    "FurnitureClassifier",
    "InvalidClassifierImageError",
    "ModelOutputError",
    "SUPPORTED_CLASSES",
    "UnreadableImageError",
    "image_classifier",
]
