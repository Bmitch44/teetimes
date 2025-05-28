from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlmodel import Session
from typing import List, Optional
from datetime import date as py_date, datetime

from src.db import (
    get_session,
    get_all_tee_times,
    get_tee_times_by_date,
    get_tee_times_by_course,
    get_tee_time_by_id,
    get_tee_times_by_course_and_date,
    get_all_courses,
    get_course_by_id,
    get_courses_by_resort
)
# Ensuring models are imported correctly for response_model hints
from src.models import TeeTimeRead, CourseRead # Using Read models for responses
from src.services.scraping_service import run_scheduled_scrape

router = APIRouter(
    prefix="/tee-times", 
    tags=["Tee Times & Courses"], 
)

# Helper for date validation
def validate_date_format(date_str: str) -> py_date:
    """Helper function to validate date strings and convert to date objects."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

# 1. Scraping Trigger Endpoint
@router.post("/scrape", summary="Trigger a new scrape for tee times")
async def trigger_scrape_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    scrape_date_str: Optional[str] = Query(
        None, 
        description="Date to scrape in YYYY-MM-DD format. Defaults to today if not provided."
    )
):
    """
    Initiates the tee time scraping process for a specified date.
    If no date is provided, scraping is done for the current day.
    The process runs in the background.
    """
    actual_scrape_date_obj = None
    if scrape_date_str:
        actual_scrape_date_obj = validate_date_format(scrape_date_str)
    else:
        actual_scrape_date_obj = py_date.today()
    
    actual_scrape_date_str = actual_scrape_date_obj.strftime("%Y-%m-%d")
    
    background_tasks.add_task(run_scheduled_scrape, db, actual_scrape_date_str)
    return {"message": "Scraping process initiated in the background.", "scrape_date": actual_scrape_date_str}

# 2. Tee Time Read Endpoints

@router.get("/", response_model=List[TeeTimeRead], summary="Get all tee times")
async def read_all_tee_times_endpoint(
    skip: int = Query(0, ge=0, description="Number of tee times to skip from the start."), 
    limit: int = Query(100, ge=1, le=200, description="Maximum number of tee times to return."), 
    db: Session = Depends(get_session)
):
    """
    Retrieves a paginated list of all tee times available in the database.
    Use 'skip' and 'limit' query parameters for pagination.
    """
    tee_times = get_all_tee_times(db=db, skip=skip, limit=limit)
    return tee_times

@router.get("/{tee_time_id}", response_model=TeeTimeRead, summary="Get tee time by ID")
async def read_tee_time_by_id_endpoint(tee_time_id: int, db: Session = Depends(get_session)):
    """
    Retrieves a single tee time by its unique ID.
    Returns a 404 error if the tee time is not found.
    """
    tee_time = get_tee_time_by_id(tee_time_id=tee_time_id, db=db)
    if not tee_time:
        raise HTTPException(status_code=404, detail="TeeTime not found")
    return tee_time

@router.get("/date/{date_str}", response_model=List[TeeTimeRead], summary="Get tee times by date")
async def read_tee_times_by_date_str_endpoint(
    date_str: str, 
    skip: int = Query(0, ge=0, description="Number of tee times to skip."), 
    limit: int = Query(100, ge=1, le=200, description="Maximum number of tee times to return."), 
    db: Session = Depends(get_session)
):
    """
    Retrieves a paginated list of tee times for a specific date.
    Date must be in YYYY-MM-DD format.
    """
    validated_date = validate_date_format(date_str) 
    tee_times = get_tee_times_by_date(date_str=validated_date.strftime("%Y-%m-%d"), db=db, skip=skip, limit=limit)
    return tee_times

@router.get("/course/{course_id}", response_model=List[TeeTimeRead], summary="Get tee times by course ID")
async def read_tee_times_by_course_id_endpoint(
    course_id: int, 
    skip: int = Query(0, ge=0, description="Number of tee times to skip."), 
    limit: int = Query(100, ge=1, le=200, description="Maximum number of tee times to return."), 
    db: Session = Depends(get_session)
):
    """
    Retrieves a paginated list of tee times for a specific course, identified by its ID.
    """
    # Optional: Check if course_id exists first could be added here if desired
    # course = get_course_by_id(course_id=course_id, db=db)
    # if not course:
    #     raise HTTPException(status_code=404, detail=f"Course with id {course_id} not found.")
    tee_times = get_tee_times_by_course(course_id=course_id, db=db, skip=skip, limit=limit)
    return tee_times

@router.get("/course/{course_id}/date/{date_str}", response_model=List[TeeTimeRead], summary="Get tee times by course ID and date")
async def read_tee_times_by_course_id_and_date_str_endpoint(
    course_id: int, 
    date_str: str, 
    skip: int = Query(0, ge=0, description="Number of tee times to skip."), 
    limit: int = Query(100, ge=1, le=200, description="Maximum number of tee times to return."), 
    db: Session = Depends(get_session)
):
    """
    Retrieves a paginated list of tee times for a specific course ID and a specific date.
    Date must be in YYYY-MM-DD format.
    """
    validated_date = validate_date_format(date_str)
    # Optional: Check if course_id exists first
    tee_times = get_tee_times_by_course_and_date(
        course_id=course_id, 
        date_str=validated_date.strftime("%Y-%m-%d"), 
        db=db, 
        skip=skip, 
        limit=limit
    )
    return tee_times

# 3. Course Read Endpoints

@router.get("/courses/", response_model=List[CourseRead], summary="Get all courses")
async def read_all_courses_endpoint(db: Session = Depends(get_session)):
    """
    Retrieves a list of all golf courses available in the database.
    """
    courses = get_all_courses(db=db)
    return courses

@router.get("/courses/{course_id}", response_model=CourseRead, summary="Get course by ID")
async def read_course_by_id_endpoint(course_id: int, db: Session = Depends(get_session)):
    """
    Retrieves a single golf course by its unique ID.
    Returns a 404 error if the course is not found.
    """
    course = get_course_by_id(course_id=course_id, db=db)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.get("/courses/resort/{resort_name}", response_model=List[CourseRead], summary="Get courses by resort name")
async def read_courses_by_resort_name_endpoint(resort_name: str, db: Session = Depends(get_session)):
    """
    Retrieves a list of golf courses associated with a specific resort name.
    Returns a 404 error if no courses are found for the given resort.
    """
    courses = get_courses_by_resort(resort=resort_name, db=db)
    if not courses: 
        raise HTTPException(status_code=404, detail=f"No courses found for resort: {resort_name}")
    return courses
