from pydantic import BaseModel, Field


class NewsSentimentRunRequest(BaseModel):
    batch_size: int | None = Field(default=None, ge=1, le=500)
    backfill: bool = False


class NewsSentimentEnrichmentRunRequest(BaseModel):
    batch_size: int | None = Field(default=None, ge=1, le=50)


class NewsSentimentDTO(BaseModel):
    label: str
    score_positive: float
    score_negative: float
    score_neutral: float
    confidence: float
    model_name: str
    model_version: str


class NewsSentimentRunResult(BaseModel):
    scored: int
    failed: int
    pending: int
    model_name: str
    model_version: str
