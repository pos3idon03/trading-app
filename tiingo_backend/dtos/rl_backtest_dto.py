from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RlRunRequest(BaseModel):
    symbol: str
    model_type: str = "rl_ddqn"
    params: dict[str, Any] = Field(default_factory=dict)
    timeframe: str = "1d"
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    model_id: Optional[UUID] = None


class RlSavedModelDTO(BaseModel):
    id: UUID
    name: str
    model_type: str
    symbol: Optional[str] = None
    timeframe: str
    created_at: datetime


class RlSavedModelsResponse(BaseModel):
    models: list[RlSavedModelDTO] = Field(default_factory=list)


class RlTrainRequest(RlRunRequest):
    name: Optional[str] = None


class RlModelCatalogItemDTO(BaseModel):
    id: str
    label: str
    description: str
    params: dict[str, Any]
    constraints: dict[str, Any] = Field(default_factory=dict)


class RlModelCatalogResponse(BaseModel):
    models: list[RlModelCatalogItemDTO]


class RlTrainResponse(BaseModel):
    id: UUID
    name: str
    model_type: str
    train_metrics: dict[str, Any] = Field(default_factory=dict)


class RlRunResponse(BaseModel):
    symbol: str
    model_type: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    train_reward: float = 0.0
    model_id: Optional[UUID] = None


class MlUniverseRunRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    universe_id: Optional[int] = None
    signals_by_symbol: dict[str, list[str]] = Field(default_factory=dict)
    timeframe: str = "1d"
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    initial_cash: float = Field(default=10_000.0, gt=0)
    commission_bps: float = Field(default=5.0, ge=0)
    slippage_bps: float = Field(default=0.0, ge=0)
    sizing_params: dict[str, Any] = Field(default_factory=dict)


class UniverseDefinitionDTO(BaseModel):
    id: int
    name: str
    source: Optional[str] = None
    description: Optional[str] = None


class UniverseListResponse(BaseModel):
    universes: list[UniverseDefinitionDTO]
