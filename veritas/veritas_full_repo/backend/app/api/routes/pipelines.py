from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.pipeline import PipelineCreate, PipelineItemResponse, PipelineListResponse, PipelineValidationRequest, PipelineValidationResponse
from app.services.pipeline_service import PipelineService
from app.services.pipeline_yaml_validator import PipelineYamlValidator

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.get("", response_model=PipelineListResponse)
def list_pipelines(db: Session = Depends(get_db)):
    return {"data": PipelineService.list(db)}


@router.post("", response_model=PipelineItemResponse)
def create_pipeline(payload: PipelineCreate, db: Session = Depends(get_db)):
    return {"data": PipelineService.create(db, payload)}


@router.post('/validate', response_model=PipelineValidationResponse)
def validate_pipeline_yaml(payload: PipelineValidationRequest):
    return {'data': PipelineYamlValidator.validate(payload.yaml_definition)}
