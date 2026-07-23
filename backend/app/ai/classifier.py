"""Model-backed furniture classification with an explicit development fallback."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from app.config import get_classifier_settings

from .labels import DISPLAY_NAMES, SUPPORTED_LABELS
from .model_loader import (
    ClassifierUnavailableError,
    ModelOutputError,
    OnnxModelLoader,
    onnx_model_loader,
)
from .preprocessing import InvalidClassifierImageError, preprocess_image


@dataclass(frozen=True)
class Prediction:
    key: str
    name: str
    confidence: float


@dataclass(frozen=True)
class ClassificationResult:
    predicted_class: str
    display_name: str
    confidence: float
    confidence_threshold: float
    predictions: tuple[Prediction, ...]
    passes_threshold: bool
    model_backend: str
    model_version: str
    model_mode: str
    inference_ms: float


def _probabilities(output: Any, output_is_logits: bool) -> Any:
    import numpy as np

    values = np.asarray(output, dtype=np.float64).squeeze()
    if values.shape != (len(SUPPORTED_LABELS),) or not np.all(np.isfinite(values)):
        raise ModelOutputError("Classifier output must contain one finite value per supported label.")
    if output_is_logits:
        shifted = values - np.max(values)
        exponentials = np.exp(shifted)
        values = exponentials / exponentials.sum()
    if np.any(values < 0) or not np.isclose(values.sum(), 1.0, atol=1e-3):
        raise ModelOutputError("Classifier probabilities must be nonnegative and sum to one.")
    return values / values.sum()


class FurnitureClassifier:
    def __init__(self, loader: OnnxModelLoader = onnx_model_loader) -> None:
        self.loader = loader

    def _development_fallback(self, tensor: Any) -> Any:
        """Non-trained color statistics; enabled only by an explicit environment flag."""
        import numpy as np

        channel_means = tensor.mean(axis=(0, 2, 3))
        raw = np.asarray(
            [
                abs(channel_means[0]) + 0.2,
                abs(channel_means[1]) + 0.2,
                abs(channel_means[2]) + 0.2,
                abs(channel_means.mean()) + 0.2,
                abs(channel_means.max() - channel_means.min()) + 0.2,
            ],
            dtype=np.float64,
        )
        return raw / raw.sum()

    def classify_image(self, image_path: Path) -> ClassificationResult:
        settings = get_classifier_settings()
        if not settings.enabled:
            raise ClassifierUnavailableError("Furniture classification is disabled.")
        started = perf_counter()
        mode = "trained_model"
        try:
            session, input_name = self.loader.get_session()
            tensor = preprocess_image(image_path)
            try:
                outputs = session.run(None, {input_name: tensor})
            except Exception as error:
                raise ClassifierUnavailableError(
                    "The classifier could not complete local inference."
                ) from error
            if len(outputs) != 1:
                raise ModelOutputError("The classifier must return exactly one output tensor.")
            probabilities = _probabilities(outputs[0], settings.output_is_logits)
        except ClassifierUnavailableError:
            if not settings.development_fallback:
                raise
            tensor = preprocess_image(image_path)
            probabilities = self._development_fallback(tensor)
            mode = "development_fallback"
        except ModelOutputError:
            raise
        except RuntimeError as error:
            raise ClassifierUnavailableError(
                "The classifier numerical runtime is unavailable."
            ) from error

        ranked = sorted(
            (
                Prediction(label, DISPLAY_NAMES[label], round(float(probabilities[index]), 6))
                for index, label in enumerate(SUPPORTED_LABELS)
            ),
            key=lambda item: item.confidence,
            reverse=True,
        )
        best = ranked[0]
        return ClassificationResult(
            predicted_class=best.key,
            display_name=best.name,
            confidence=best.confidence,
            confidence_threshold=settings.min_confidence,
            predictions=tuple(ranked),
            passes_threshold=best.confidence >= settings.min_confidence,
            model_backend=settings.backend,
            model_version=settings.version,
            model_mode=mode,
            inference_ms=round((perf_counter() - started) * 1000, 3),
        )

    def health(self) -> dict[str, object]:
        settings = get_classifier_settings()
        loader_status = self.loader.status()
        if settings.development_fallback and settings.enabled and loader_status != "ready":
            loader_status = "ready"
            mode = "development_fallback"
        else:
            mode = "trained_model" if loader_status == "ready" else "unavailable"
        return {
            "status": loader_status,
            "enabled": settings.enabled,
            "backend": settings.backend,
            "model_version": settings.version,
            "mode": mode,
            "supported_labels": list(SUPPORTED_LABELS),
        }


furniture_classifier = FurnitureClassifier()

__all__ = [
    "ClassificationResult",
    "ClassifierUnavailableError",
    "FurnitureClassifier",
    "InvalidClassifierImageError",
    "ModelOutputError",
    "Prediction",
    "furniture_classifier",
]
