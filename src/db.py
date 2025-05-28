from sqlmodel import SQLModel, create_engine, Session, select
from typing import List, Optional # Add Optional for TeeTime | None

# Import models from the models directory
# Assuming models.py is in src.models
from .models import Course, TeeTime # Adjusted import path

DATABASE_URL = "sqlite:///teetimes.db"
engine = create_engine(DATABASE_URL, echo=True) # Add echo for debugging if needed

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session(): # Changed from get_db_session to get_session to match instructions
    with Session(engine) as session:
        yield session

# Functions moved from old_main.py
def insert_courses(courses: List[Course], db: Session): # Added db: Session parameter
    try:
        for course in courses:
            existing = db.exec(
                select(Course).where(Course.value == course.value)
            ).first()
            if existing:
                existing.label = course.label
                # Add more fields if needed
            else:
                db.add(course)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error inserting courses: {e}") # Added f-string and error details

def get_course_by_id(course_id: int, db: Session) -> Course: # Added db: Session parameter
    return db.exec(select(Course).where(Course.id == course_id)).first()

def get_courses_by_resort(resort: str, db: Session) -> List[Course]: # Added db: Session parameter
    return db.exec(select(Course).where(Course.resort == resort)).all()

def get_all_courses(db: Session) -> List[Course]: # Added db: Session parameter
    return db.exec(select(Course)).all()

def insert_tee_times(tee_times: List[TeeTime], db: Session): # Added db: Session parameter
    try:
        for tee_time in tee_times:
            existing = db.exec(
                select(TeeTime).where(
                    TeeTime.course_id == tee_time.course_id,
                    TeeTime.time == tee_time.time,
                    TeeTime.date == tee_time.date
                )
            ).first()
            if existing:
                existing.players = tee_time.players
                existing.price = tee_time.price
                # Add more fields if needed
            else:
                db.add(tee_time)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error inserting tee times: {e}") # Added f-string and error details

# New functions for querying tee times

def get_all_tee_times(db: Session, skip: int = 0, limit: int = 100) -> List[TeeTime]:
    """Queries and returns a list of all TeeTime objects with pagination."""
    statement = select(TeeTime).offset(skip).limit(limit)
    return db.exec(statement).all()

def get_tee_times_by_date(date_str: str, db: Session, skip: int = 0, limit: int = 100) -> List[TeeTime]:
    """Queries TeeTime objects filtering by the date field, with pagination."""
    statement = select(TeeTime).where(TeeTime.date == date_str).offset(skip).limit(limit)
    return db.exec(statement).all()

def get_tee_times_by_course(course_id: int, db: Session, skip: int = 0, limit: int = 100) -> List[TeeTime]:
    """Queries TeeTime objects filtering by course_id, with pagination."""
    statement = select(TeeTime).where(TeeTime.course_id == course_id).offset(skip).limit(limit)
    return db.exec(statement).all()

def get_tee_time_by_id(tee_time_id: int, db: Session) -> Optional[TeeTime]: # Use Optional for TeeTime | None
    """Queries for a single TeeTime by its id."""
    statement = select(TeeTime).where(TeeTime.id == tee_time_id)
    return db.exec(statement).first()

def get_tee_times_by_course_and_date(course_id: int, date_str: str, db: Session, skip: int = 0, limit: int = 100) -> List[TeeTime]:
    """Queries TeeTime objects filtering by both course_id and date, with pagination."""
    statement = select(TeeTime).where(TeeTime.course_id == course_id, TeeTime.date == date_str).offset(skip).limit(limit)
    return db.exec(statement).all()
