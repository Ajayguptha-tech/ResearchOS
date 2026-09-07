from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=3)
    domain: str = Field(..., min_length=2)
    description: str | None = None


class ResearchIdeaRequest(BaseModel):
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)


class PlanCreateRequest(BaseModel):
    idea_id: int | None = None
