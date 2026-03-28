from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


T = TypeVar("T")


class DataResponse(BaseModel, Generic[T]):
    data: T


class MessageResponse(BaseModel):
    message: str
