"""Course model"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.tee_time import TeeTime

from sqlmodel import Field, Relationship, SQLModel


class Course(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True, description="Unique identifier for the course")
    value: str = Field(description="Internal or scraper-specific value/identifier for the course, often used in URLs or scraping logic")
    label: str = Field(unique=True, description="User-friendly display name for the course")
    resort: str = Field(description="Name of the resort or club the course belongs to")
    holes: int = Field(description="Number of holes the course has (e.g., 9 or 18)")
    url: str = Field(description="Official URL for the course or its booking page")
# No newline at end of file

    tee_times: list["TeeTime"] = Relationship(back_populates="course")

# Pydantic model for API responses (Read model)
class CourseRead(SQLModel): # Inheriting from SQLModel is fine for response models
    id: int
    value: str
    label: str
    resort: str
    holes: int
    url: str