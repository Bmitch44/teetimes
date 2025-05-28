# tests/test_db.py
import pytest
from sqlmodel import Session
from typing import List

from src.db import (
    insert_courses, get_course_by_id, get_courses_by_resort, get_all_courses,
    insert_tee_times, get_all_tee_times, get_tee_times_by_date,
    get_tee_times_by_course, get_tee_time_by_id, get_tee_times_by_course_and_date
)
from src.models import Course, TeeTime

# Fixture db_session_test is from conftest.py

# --- Test Course DB Functions ---

def test_insert_courses_new(db_session_test: Session):
    courses_data = [
        Course(value="CourseDB1", label="CDB1", resort="ResortDB", holes=18, url="http://db1.com"),
        Course(value="CourseDB2", label="CDB2", resort="ResortDB", holes=9, url="http://db2.com")
    ]
    insert_courses(courses_data, db_session_test)

    retrieved_courses = get_all_courses(db_session_test)
    assert len(retrieved_courses) == 2
    labels = {c.label for c in retrieved_courses}
    assert "CDB1" in labels
    assert "CDB2" in labels

def test_insert_courses_update_existing(db_session_test: Session):
    course1_v1 = Course(value="UniqueCourseVal", label="OldLabel", resort="OldResort", holes=18, url="http://old.com")
    insert_courses([course1_v1], db_session_test)
    
    retrieved_v1 = get_all_courses(db_session_test)[0]
    assert retrieved_v1.label == "OldLabel"

    course1_v2 = Course(value="UniqueCourseVal", label="NewLabel", resort="NewResort", holes=18, url="http://new.com")
    insert_courses([course1_v2], db_session_test)

    retrieved_courses = get_all_courses(db_session_test)
    assert len(retrieved_courses) == 1 # Should not create a new one
    retrieved_v2 = retrieved_courses[0]
    assert retrieved_v2.label == "NewLabel" # Check if updated
    assert retrieved_v2.resort == "OldResort" # Only label should update based on current insert_courses logic

def test_get_all_courses_empty(db_session_test: Session):
    courses = get_all_courses(db_session_test)
    assert courses == []

def test_get_course_by_id(db_session_test: Session):
    course_data = Course(value="CourseByID", label="CID", resort="ResortID", holes=18, url="http://cid.com")
    insert_courses([course_data], db_session_test)
    # Need to get the actual inserted course to know its ID
    inserted_course = get_all_courses(db_session_test)[0]
    
    retrieved_course = get_course_by_id(inserted_course.id, db_session_test)
    assert retrieved_course is not None
    assert retrieved_course.label == "CID"
    
    assert get_course_by_id(9999, db_session_test) is None

def test_get_courses_by_resort(db_session_test: Session):
    c1 = Course(value="ResA_C1", label="RAC1", resort="ResortA", holes=18, url="http://ra1.com")
    c2 = Course(value="ResA_C2", label="RAC2", resort="ResortA", holes=9, url="http://ra2.com")
    c3 = Course(value="ResB_C1", label="RBC1", resort="ResortB", holes=18, url="http://rb1.com")
    insert_courses([c1, c2, c3], db_session_test)

    resort_a_courses = get_courses_by_resort("ResortA", db_session_test)
    assert len(resort_a_courses) == 2
    resort_b_courses = get_courses_by_resort("ResortB", db_session_test)
    assert len(resort_b_courses) == 1
    assert resort_b_courses[0].label == "RBC1"
    
    assert get_courses_by_resort("NonExistentResort", db_session_test) == []

# --- Test TeeTime DB Functions ---

def test_insert_tee_times_new(db_session_test: Session):
    course = Course(value="TT_Course1", label="TTC1", resort="TTResort", holes=18, url="http://ttc1.com")
    insert_courses([course], db_session_test)
    db_course = get_all_courses(db_session_test)[0] # Get the course with its ID

    tee_times_data = [
        TeeTime(course_id=db_course.id, date="2024-07-25", time="10:00", players=4, price=50),
        TeeTime(course_id=db_course.id, date="2024-07-25", time="10:10", players=2, price=55)
    ]
    insert_tee_times(tee_times_data, db_session_test)

    retrieved_tee_times = get_all_tee_times(db_session_test)
    assert len(retrieved_tee_times) == 2
    times = {tt.time for tt in retrieved_tee_times}
    assert "10:00" in times
    assert "10:10" in times

def test_insert_tee_times_update_existing(db_session_test: Session):
    course = Course(value="TT_Course_Upd", label="TTC_U", resort="TTResortU", holes=18, url="http://ttcu.com")
    insert_courses([course], db_session_test)
    db_course = get_all_courses(db_session_test)[0]

    tt_v1 = TeeTime(course_id=db_course.id, date="2024-07-26", time="11:00", players=2, price=30)
    insert_tee_times([tt_v1], db_session_test)
    retrieved_v1 = get_all_tee_times(db_session_test)[0]
    assert retrieved_v1.players == 2
    assert retrieved_v1.price == 30

    tt_v2 = TeeTime(course_id=db_course.id, date="2024-07-26", time="11:00", players=4, price=35) # Same key, different players/price
    insert_tee_times([tt_v2], db_session_test)
    
    all_tts = get_all_tee_times(db_session_test)
    assert len(all_tts) == 1 # Should update, not insert new
    retrieved_v2 = all_tts[0]
    assert retrieved_v2.players == 4
    assert retrieved_v2.price == 35

def test_get_all_tee_times_empty(db_session_test: Session):
    tts = get_all_tee_times(db_session_test)
    assert tts == []

def test_get_all_tee_times_pagination(db_session_test: Session):
    course = Course(value="TT_Course_Pag", label="TTC_P", resort="TTResortP", holes=18, url="http://ttcp.com")
    insert_courses([course], db_session_test)
    db_course = get_all_courses(db_session_test)[0]

    for i in range(5):
        insert_tee_times([TeeTime(course_id=db_course.id, date="2024-07-27", time=f"10:0{i}", players=2, price=20+i)], db_session_test)
    
    tts_page1 = get_all_tee_times(db_session_test, skip=0, limit=3)
    assert len(tts_page1) == 3
    tts_page2 = get_all_tee_times(db_session_test, skip=3, limit=3)
    assert len(tts_page2) == 2

def test_get_tee_time_by_id(db_session_test: Session):
    course = Course(value="TT_Course_ID", label="TTC_ID", resort="TTResortID", holes=18, url="http://ttcid.com")
    insert_courses([course], db_session_test)
    db_course = get_all_courses(db_session_test)[0]
    
    tt_data = TeeTime(course_id=db_course.id, date="2024-07-28", time="12:00", players=3, price=40)
    insert_tee_times([tt_data], db_session_test)
    inserted_tt = get_all_tee_times(db_session_test)[0] # Get the actual tee time with ID

    retrieved_tt = get_tee_time_by_id(inserted_tt.id, db_session_test)
    assert retrieved_tt is not None
    assert retrieved_tt.time == "12:00"
    assert get_tee_time_by_id(9999, db_session_test) is None

def test_get_tee_times_by_date(db_session_test: Session):
    course = Course(value="TT_Course_Date", label="TTC_D", resort="TTResortD", holes=18, url="http://ttcd.com")
    insert_courses([course], db_session_test)
    db_course = get_all_courses(db_session_test)[0]

    tt1 = TeeTime(course_id=db_course.id, date="2024-07-29", time="13:00", players=2, price=30)
    tt2 = TeeTime(course_id=db_course.id, date="2024-07-29", time="14:00", players=4, price=50)
    tt3 = TeeTime(course_id=db_course.id, date="2024-07-30", time="15:00", players=3, price=40)
    insert_tee_times([tt1, tt2, tt3], db_session_test)

    date1_tts = get_tee_times_by_date("2024-07-29", db_session_test)
    assert len(date1_tts) == 2
    date2_tts = get_tee_times_by_date("2024-07-30", db_session_test)
    assert len(date2_tts) == 1
    assert date2_tts[0].time == "15:00"
    assert get_tee_times_by_date("2024-08-01", db_session_test) == []

def test_get_tee_times_by_course(db_session_test: Session):
    c1 = Course(value="TTC_C1", label="TTC1", resort="TTC_Res", holes=18, url="http://ttcc1.com")
    c2 = Course(value="TTC_C2", label="TTC2", resort="TTC_Res", holes=18, url="http://ttcc2.com")
    insert_courses([c1, c2], db_session_test)
    db_c1 = get_all_courses(db_session_test)[0]
    db_c2 = get_all_courses(db_session_test)[1]


    tt_c1 = TeeTime(course_id=db_c1.id, date="2024-07-31", time="16:00", players=2, price=30)
    tt_c2 = TeeTime(course_id=db_c2.id, date="2024-07-31", time="17:00", players=4, price=50)
    insert_tee_times([tt_c1, tt_c2], db_session_test)

    c1_tts = get_tee_times_by_course(db_c1.id, db_session_test)
    assert len(c1_tts) == 1
    assert c1_tts[0].time == "16:00"
    
    c2_tts = get_tee_times_by_course(db_c2.id, db_session_test)
    assert len(c2_tts) == 1
    assert c2_tts[0].time == "17:00"
    
    assert get_tee_times_by_course(9999, db_session_test) == [] # Non-existent course_id

def test_get_tee_times_by_course_and_date(db_session_test: Session):
    c1 = Course(value="TTC_CD1", label="TCD1", resort="TCD_Res", holes=18, url="http://tccd1.com")
    insert_courses([c1], db_session_test)
    db_c1 = get_all_courses(db_session_test)[0]

    tt1 = TeeTime(course_id=db_c1.id, date="2024-08-01", time="09:00", players=2, price=30)
    tt2 = TeeTime(course_id=db_c1.id, date="2024-08-01", time="10:00", players=4, price=50) # Same course, same date
    tt3 = TeeTime(course_id=db_c1.id, date="2024-08-02", time="11:00", players=3, price=40) # Same course, diff date
    insert_tee_times([tt1, tt2, tt3], db_session_test)

    res_d1 = get_tee_times_by_course_and_date(db_c1.id, "2024-08-01", db_session_test)
    assert len(res_d1) == 2
    
    res_d2 = get_tee_times_by_course_and_date(db_c1.id, "2024-08-02", db_session_test)
    assert len(res_d2) == 1
    assert res_d2[0].time == "11:00"

    assert get_tee_times_by_course_and_date(db_c1.id, "2024-08-03", db_session_test) == [] # Correct course, wrong date
    assert get_tee_times_by_course_and_date(9999, "2024-08-01", db_session_test) == [] # Wrong course, correct date

def test_pagination_for_filtered_queries(db_session_test: Session):
    course = Course(value="TT_Course_FiltPag", label="TTC_FP", resort="TTResortFP", holes=18, url="http://ttcfp.com")
    insert_courses([course], db_session_test)
    db_course = get_all_courses(db_session_test)[0]
    target_date = "2024-08-05"

    for i in range(5):
        insert_tee_times([TeeTime(course_id=db_course.id, date=target_date, time=f"11:0{i}", players=2, price=20+i)], db_session_test)
    insert_tee_times([TeeTime(course_id=db_course.id, date="2024-08-06", time="12:00", players=2, price=30)], db_session_test) # Different date

    # Test get_tee_times_by_date with pagination
    tts_date_p1 = get_tee_times_by_date(target_date, db_session_test, skip=0, limit=3)
    assert len(tts_date_p1) == 3
    tts_date_p2 = get_tee_times_by_date(target_date, db_session_test, skip=3, limit=3)
    assert len(tts_date_p2) == 2

    # Test get_tee_times_by_course with pagination
    tts_course_p1 = get_tee_times_by_course(db_course.id, db_session_test, skip=0, limit=3)
    assert len(tts_course_p1) == 3 # Includes the one from 2024-08-06 for this course
    # Re-evaluate: get_tee_times_by_course will fetch all for this course, so 6 total
    # This needs to be adjusted if we only want for `target_date`
    # The previous loop created 5 for target_date, and 1 for 2024-08-06. Total 6 for db_course.id
    
    # Correcting based on actual data:
    all_for_course = get_tee_times_by_course(db_course.id, db_session_test, limit=10) # Get all for this course
    assert len(all_for_course) == 6 
    
    tts_course_p1_corrected = get_tee_times_by_course(db_course.id, db_session_test, skip=0, limit=4)
    assert len(tts_course_p1_corrected) == 4
    tts_course_p2_corrected = get_tee_times_by_course(db_course.id, db_session_test, skip=4, limit=4)
    assert len(tts_course_p2_corrected) == 2


    # Test get_tee_times_by_course_and_date with pagination
    tts_course_date_p1 = get_tee_times_by_course_and_date(db_course.id, target_date, db_session_test, skip=0, limit=3)
    assert len(tts_course_date_p1) == 3
    tts_course_date_p2 = get_tee_times_by_course_and_date(db_course.id, target_date, db_session_test, skip=3, limit=3)
    assert len(tts_course_date_p2) == 2
