from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dataset import (
    DatasetCreate,
    DatasetDiseaseListResponse,
    DatasetItemResponse,
    DatasetListResponse,
    DatasetValidationResponse,
)
from app.services.dataset_service import DatasetService
from app.services.dataset_validation import DatasetValidationService

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=DatasetListResponse)
def list_datasets(
    disease: str | None = Query(default=None),
    benchmark_only: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return {"data": DatasetService.list(db, disease=disease, benchmark_only=benchmark_only)}


@router.get("/diseases", response_model=DatasetDiseaseListResponse)
def list_dataset_diseases(db: Session = Depends(get_db)):
    return {"data": DatasetService.list_diseases(db)}


@router.get("/{dataset_ref}", response_model=DatasetItemResponse)
def get_dataset(dataset_ref: str, db: Session = Depends(get_db)):
    item = DatasetService.detail(db, dataset_ref)
    if not item:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"data": item}


@router.post("", response_model=DatasetItemResponse)
def create_dataset(payload: DatasetCreate, db: Session = Depends(get_db)):
    return {"data": DatasetService.create(db, payload)}


@router.post("/{dataset_ref}/validate", response_model=DatasetValidationResponse)
def validate_dataset(dataset_ref: str, db: Session = Depends(get_db)):
    result = DatasetValidationService.validate_by_ref(db, dataset_ref)
    if not result:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"data": result}
