"""Public readiness metadata for the optional local classifier."""

from fastapi import APIRouter

from app.ai.classifier import furniture_classifier
from app.schemas.classification import ClassifierHealthRead

router = APIRouter(tags=["Health"])


@router.get("/health/classifier", response_model=ClassifierHealthRead)
def classifier_health() -> ClassifierHealthRead:
    return ClassifierHealthRead.model_validate(furniture_classifier.health())
