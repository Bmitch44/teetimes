"""
Tee Time Model
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.course import Course

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import UniqueConstraint


class TeeTime(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True, description="Unique identifier for the tee time slot")
    course_id: int = Field(foreign_key="course.id", description="Foreign key linking to the course this tee time belongs to")
    time: str = Field(description="Tee time in HH:MM format (e.g., '08:30')")
    date: str = Field(description="Date of the tee time in YYYY-MM-DD format (e.g., '2024-07-15')")
    players: int = Field(description="Number of available player slots for this tee time")
    price: str = Field(description="Price for this tee time, as a string (e.g., '55.00', may include currency symbols or text)") # Consider Decimal/float if processing
    holes: int = Field(description="Number of holes this tee time is for (e.g., 9 or 18)")

    course: "Course" = Relationship(back_populates="tee_times")
    __table_args__ = (UniqueConstraint("course_id", "time", "date"),)

# Pydantic model for API responses (Read model)
# Need to import CourseRead from .course
from typing import Optional # Ensure Optional is imported if not already
from .course import CourseRead

class TeeTimeRead(SQLModel): # Inheriting from SQLModel is fine
    id: int
    course_id: int
    time: str
    date: str
    players: int
    price: str 
    holes: int
    course: Optional[CourseRead] = None
# No newline at end of file