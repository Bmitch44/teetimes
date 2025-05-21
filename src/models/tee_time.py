"""
Tee Time Model
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.course import Course

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import UniqueConstraint


class TeeTime(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id")
    time: str
    date: str
    players: int
    price: str

    course: "Course" = Relationship(back_populates="tee_times")
    __table_args__ = (UniqueConstraint("course_id", "time", "date"),)