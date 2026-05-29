from pydantic import BaseModel, Field


class ProbabilityContributorDTO(BaseModel):
    feature: str
    value: float
    contribution: float


class ProbabilityExplainabilityDTO(BaseModel):
    method: str
    top_contributors: list[ProbabilityContributorDTO] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
