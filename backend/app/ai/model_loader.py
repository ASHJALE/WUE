"""Lazy, once-per-process ONNX Runtime model loader."""

from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock
from typing import Any

from app.config import get_classifier_settings

logger = logging.getLogger(__name__)


class ClassifierUnavailableError(RuntimeError):
    """The configured classifier cannot currently serve inference."""


class ModelOutputError(RuntimeError):
    """The model returned an output incompatible with WUE labels."""


class OnnxModelLoader:
    """Load one configured ONNX session and retain controlled failure state."""

    def __init__(self) -> None:
        self._session: Any | None = None
        self._input_name: str | None = None
        self._load_error: str | None = None
        self._load_attempted = False
        self._load_count = 0
        self._lock = Lock()

    @property
    def load_count(self) -> int:
        return self._load_count

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def reset_for_tests(self) -> None:
        with self._lock:
            self._session = None
            self._input_name = None
            self._load_error = None
            self._load_attempted = False
            self._load_count = 0

    def _load(self) -> None:
        settings = get_classifier_settings()
        self._load_attempted = True
        self._load_count += 1
        if not settings.enabled:
            self._load_error = "Classifier is disabled."
            return
        if settings.backend != "onnx":
            self._load_error = "Only the ONNX classifier backend is supported."
            return
        if not settings.model_path.is_file():
            self._load_error = "Configured classifier artifact is unavailable."
            return
        try:
            import onnxruntime as ort

            self._session = ort.InferenceSession(
                str(settings.model_path),
                providers=["CPUExecutionProvider"],
            )
            inputs = self._session.get_inputs()
            if len(inputs) != 1:
                raise ModelOutputError("The classifier must expose exactly one input.")
            self._input_name = inputs[0].name
            logger.info(
                "WUE furniture classifier loaded (backend=%s, version=%s).",
                settings.backend,
                settings.version,
            )
        except Exception as error:
            # Provider-specific ONNX Runtime errors share no stable base class;
            # keep every loader failure behind this controlled boundary.
            self._session = None
            self._input_name = None
            self._load_error = "The configured ONNX classifier could not be loaded."
            logger.warning("WUE furniture classifier is unavailable: %s", type(error).__name__)

    def get_session(self) -> tuple[Any, str]:
        if not self._load_attempted:
            with self._lock:
                if not self._load_attempted:
                    self._load()
        if self._session is None or self._input_name is None:
            raise ClassifierUnavailableError(self._load_error or "Classifier is unavailable.")
        return self._session, self._input_name

    def status(self) -> str:
        settings = get_classifier_settings()
        if not settings.enabled:
            return "disabled"
        if self._session is not None:
            return "ready"
        if not settings.model_path.is_file():
            return "unavailable"
        if not self._load_attempted:
            try:
                self.get_session()
            except ClassifierUnavailableError:
                pass
        return "ready" if self._session is not None else "error"


onnx_model_loader = OnnxModelLoader()
