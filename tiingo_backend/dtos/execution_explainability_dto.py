from pydantic import BaseModel, Field


class ProbabilityContributorDTO(BaseModel):
    feature: str
    value: float
    contribution: float


class ProbabilityExplainabilityDTO(BaseModel):
    method: str
    base_value: float | None = None
    predicted_value: float | None = None
    top_contributors: list[ProbabilityContributorDTO] = Field(default_factory=list)
    ordered_contributors: list[ProbabilityContributorDTO] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
