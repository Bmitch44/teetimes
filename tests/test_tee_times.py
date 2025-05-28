# tests/test_tee_times.py
from fastapi.testclient import TestClient
from sqlmodel import Session
from src.models import Course, TeeTime # Import your models
from datetime import datetime as dt, date as py_date, timedelta
from unittest.mock import patch

# client_test and db_session_test are fixtures from conftest.py

def test_read_root(client_test: TestClient):
    response = client_test.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Tee Time API. Navigate to /docs for API documentation."}

# --- Course API Tests ---
def test_read_all_courses_empty(client_test: TestClient):
    response = client_test.get("/api/v1/tee-times/courses/") 
    assert response.status_code == 200
    assert response.json() == []

def test_create_and_read_course(client_test: TestClient, db_session_test: Session):
    course_data = {"value": "Test Course", "label": "TestLabel", "resort": "TestResort", "holes": 18, "url": "http://example.com/test"}
    new_course = Course(**course_data)
    
    db_session_test.add(new_course)
    db_session_test.commit()
    db_session_test.refresh(new_course)

    assert new_course.id is not None

    # Test read by ID
    response = client_test.get(f"/api/v1/tee-times/courses/{new_course.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["label"] == "TestLabel"
    assert data["resort"] == "TestResort"
    assert data["id"] == new_course.id

    # Test getting all courses
    response_all = client_test.get("/api/v1/tee-times/courses/")
    assert response_all.status_code == 200
    assert len(response_all.json()) == 1
    assert response_all.json()[0]["label"] == "TestLabel"

def test_course_not_found(client_test: TestClient):
    response = client_test.get("/api/v1/tee-times/courses/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Course not found"

def test_read_courses_by_resort(client_test: TestClient, db_session_test: Session):
    course1_data = {"value": "ResortA Course1", "label": "RAC1", "resort": "ResortA", "holes": 18, "url": "http://example.com/rac1"}
    course2_data = {"value": "ResortA Course2", "label": "RAC2", "resort": "ResortA", "holes": 9, "url": "http://example.com/rac2"}
    course3_data = {"value": "ResortB Course1", "label": "RBC1", "resort": "ResortB", "holes": 18, "url": "http://example.com/rbc1"}
    
    c1 = Course(**course1_data)
    c2 = Course(**course2_data)
    c3 = Course(**course3_data)
    
    db_session_test.add_all([c1, c2, c3])
    db_session_test.commit()

    # Test for ResortA
    response_a = client_test.get("/api/v1/tee-times/courses/resort/ResortA")
    assert response_a.status_code == 200
    data_a = response_a.json()
    assert len(data_a) == 2
    labels_a = {item["label"] for item in data_a}
    assert "RAC1" in labels_a
    assert "RAC2" in labels_a

    # Test for ResortB
    response_b = client_test.get("/api/v1/tee-times/courses/resort/ResortB")
    assert response_b.status_code == 200
    assert len(response_b.json()) == 1
    assert response_b.json()[0]["label"] == "RBC1"

    # Test for non-existent resort
    response_c = client_test.get("/api/v1/tee-times/courses/resort/NonExistentResort")
    assert response_c.status_code == 404 # Based on router implementation raising 404 if list is empty

# --- Tee Time API Tests ---

def test_read_all_tee_times_empty(client_test: TestClient):
    response = client_test.get("/api/v1/tee-times/")
    assert response.status_code == 200
    assert response.json() == []

def test_create_and_read_tee_time(client_test: TestClient, db_session_test: Session):
    # 1. Create a Course first
    course = Course(value="GolfCourse1", label="GC1", resort="ResortX", holes=18, url="http://example.com/gc1")
    db_session_test.add(course)
    db_session_test.commit()
    db_session_test.refresh(course)
    assert course.id is not None

    # 2. Create a TeeTime associated with that course
    tee_time_data = {
        "course_id": course.id,
        "date": "2024-07-15",
        "time": "10:00",
        "players": 4,
        "price": 50.00
    }
    # Create TeeTime model instance (assuming direct creation for now, not via API)
    new_tee_time = TeeTime(**tee_time_data)
    db_session_test.add(new_tee_time)
    db_session_test.commit()
    db_session_test.refresh(new_tee_time)
    assert new_tee_time.id is not None

    # 3. Test GET /api/v1/tee-times/{tee_time_id}
    response_single = client_test.get(f"/api/v1/tee-times/{new_tee_time.id}")
    assert response_single.status_code == 200
    data_single = response_single.json()
    assert data_single["id"] == new_tee_time.id
    assert data_single["date"] == "2024-07-15"
    assert data_single["time"] == "10:00"
    assert data_single["course_id"] == course.id

    # 4. Test GET /api/v1/tee-times/ (should list the created tee time)
    response_all = client_test.get("/api/v1/tee-times/")
    assert response_all.status_code == 200
    data_all = response_all.json()
    assert len(data_all) == 1
    assert data_all[0]["id"] == new_tee_time.id

def test_read_tee_times_by_date(client_test: TestClient, db_session_test: Session):
    course = Course(value="DateCourse", label="DC", resort="DateResort", holes=18, url="http://example.com/dc")
    db_session_test.add(course)
    db_session_test.commit()
    db_session_test.refresh(course)

    tt1 = TeeTime(course_id=course.id, date="2024-07-16", time="08:00", players=2, price=30)
    tt2 = TeeTime(course_id=course.id, date="2024-07-16", time="09:00", players=4, price=50)
    tt3 = TeeTime(course_id=course.id, date="2024-07-17", time="10:00", players=3, price=40)
    db_session_test.add_all([tt1, tt2, tt3])
    db_session_test.commit()

    # Test for date with tee times
    response_with = client_test.get("/api/v1/tee-times/date/2024-07-16")
    assert response_with.status_code == 200
    data_with = response_with.json()
    assert len(data_with) == 2
    times_retrieved = {item["time"] for item in data_with}
    assert "08:00" in times_retrieved
    assert "09:00" in times_retrieved

    # Test for date without tee times
    response_without = client_test.get("/api/v1/tee-times/date/2024-07-18")
    assert response_without.status_code == 200
    assert response_without.json() == []

    # Test with invalid date format
    response_invalid = client_test.get("/api/v1/tee-times/date/invalid-date")
    assert response_invalid.status_code == 400
    assert response_invalid.json()["detail"] == "Invalid date format. Use YYYY-MM-DD."

def test_read_tee_times_by_course(client_test: TestClient, db_session_test: Session):
    course1 = Course(value="CourseA", label="CA", resort="ResortCommon", holes=18, url="http://example.com/ca")
    course2 = Course(value="CourseB", label="CB", resort="ResortCommon", holes=18, url="http://example.com/cb")
    db_session_test.add_all([course1, course2])
    db_session_test.commit()
    db_session_test.refresh(course1)
    db_session_test.refresh(course2)

    tt_c1_1 = TeeTime(course_id=course1.id, date="2024-07-19", time="11:00", players=2, price=30)
    tt_c1_2 = TeeTime(course_id=course1.id, date="2024-07-19", time="12:00", players=4, price=50)
    tt_c2_1 = TeeTime(course_id=course2.id, date="2024-07-19", time="13:00", players=3, price=40)
    db_session_test.add_all([tt_c1_1, tt_c1_2, tt_c2_1])
    db_session_test.commit()

    # Test for Course1
    response_c1 = client_test.get(f"/api/v1/tee-times/course/{course1.id}")
    assert response_c1.status_code == 200
    data_c1 = response_c1.json()
    assert len(data_c1) == 2
    c1_times = {item["time"] for item in data_c1}
    assert "11:00" in c1_times
    assert "12:00" in c1_times

    # Test for Course2
    response_c2 = client_test.get(f"/api/v1/tee-times/course/{course2.id}")
    assert response_c2.status_code == 200
    assert len(response_c2.json()) == 1
    assert response_c2.json()[0]["time"] == "13:00"

    # Test for non-existent course ID (valid format, but doesn't exist)
    response_non_existent = client_test.get("/api/v1/tee-times/course/99999")
    assert response_non_existent.status_code == 200 # API returns empty list if course has no tee times or course does not exist
    assert response_non_existent.json() == []


def test_read_tee_times_by_course_and_date(client_test: TestClient, db_session_test: Session):
    course = Course(value="CourseDateTime", label="CDT", resort="ResortDT", holes=18, url="http://example.com/cdt")
    db_session_test.add(course)
    db_session_test.commit()
    db_session_test.refresh(course)

    tt1 = TeeTime(course_id=course.id, date="2024-07-20", time="14:00", players=2, price=30)
    tt2 = TeeTime(course_id=course.id, date="2024-07-20", time="15:00", players=4, price=50)
    tt3 = TeeTime(course_id=course.id, date="2024-07-21", time="16:00", players=3, price=40) # Different date
    db_session_test.add_all([tt1, tt2, tt3])
    db_session_test.commit()

    # Test for course and specific date with tee times
    response_match = client_test.get(f"/api/v1/tee-times/course/{course.id}/date/2024-07-20")
    assert response_match.status_code == 200
    data_match = response_match.json()
    assert len(data_match) == 2
    match_times = {item["time"] for item in data_match}
    assert "14:00" in match_times
    assert "15:00" in match_times

    # Test for course and date with no tee times
    response_no_match_date = client_test.get(f"/api/v1/tee-times/course/{course.id}/date/2024-07-22")
    assert response_no_match_date.status_code == 200
    assert response_no_match_date.json() == []
    
    # Test with invalid date format
    response_invalid_date = client_test.get(f"/api/v1/tee-times/course/{course.id}/date/invalid-date-format")
    assert response_invalid_date.status_code == 400
    assert response_invalid_date.json()["detail"] == "Invalid date format. Use YYYY-MM-DD."

def test_tee_time_not_found(client_test: TestClient):
    response = client_test.get("/api/v1/tee-times/88888") # Non-existent ID
    assert response.status_code == 404
    assert response.json()["detail"] == "TeeTime not found"

# --- Scraping Trigger Endpoint Test ---

def test_trigger_scrape_endpoint(client_test: TestClient, db_session_test: Session): # Added db_session_test
    # Patch where 'run_scheduled_scrape' is looked up (i.e., in the router module)
    with patch("src.routers.tee_times_router.run_scheduled_scrape") as mock_run_scrape:
        # Test without date parameter (should default to today)
        response_no_date = client_test.post("/api/v1/tee-times/scrape")
        assert response_no_date.status_code == 200
        json_response_no_date = response_no_date.json()
        assert "Scraping process initiated" in json_response_no_date["message"]
        today_str = py_date.today().strftime("%Y-%m-%d")
        assert json_response_no_date["scrape_date"] == today_str
        mock_run_scrape.assert_called_with(db_session_test, today_str) # db_session_test is passed by Depends

        mock_run_scrape.reset_mock()

        # Test with a specific valid date parameter
        scrape_date_param = "2025-01-01"
        response_with_date = client_test.post(f"/api/v1/tee-times/scrape?scrape_date_str={scrape_date_param}")
        assert response_with_date.status_code == 200
        json_response_with_date = response_with_date.json()
        assert "Scraping process initiated" in json_response_with_date["message"]
        assert json_response_with_date["scrape_date"] == scrape_date_param
        mock_run_scrape.assert_called_with(db_session_test, scrape_date_param)

        mock_run_scrape.reset_mock()

        # Test with an invalid date format
        invalid_date_param = "01-01-2025"
        response_invalid_date = client_test.post(f"/api/v1/tee-times/scrape?scrape_date_str={invalid_date_param}")
        assert response_invalid_date.status_code == 400
        assert "Invalid date format" in response_invalid_date.json()["detail"]
        mock_run_scrape.assert_not_called()
