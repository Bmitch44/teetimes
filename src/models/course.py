"""Course model"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.tee_time import TeeTime

from sqlmodel import Field, Relationship, SQLModel


class Course(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    value: str
    label: str = Field(unique=True)
    resort: str
    holes: int
    url: str

    tee_times: list["TeeTime"] = Relationship(back_populates="course")