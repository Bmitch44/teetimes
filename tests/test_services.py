# tests/test_services.py
import pytest
from unittest.mock import patch, MagicMock, call # Added call for checking multiple calls
from sqlmodel import Session # For type hinting if needed, though db_session_test is used

from src.services.scraping_service import (
    aggregate_and_deduplicate_tee_times,
    run_scheduled_scrape,
    COURSES as SERVICE_COURSES # Import the constant from the service
)
from src.models import TeeTime, Course

# Fixture db_session_test is from conftest.py, though not strictly needed for all service tests
# if DB interactions are fully mocked. However, run_scheduled_scrape takes a db session.

def test_aggregate_and_deduplicate_tee_times():
    # Create TeeTime objects, ensuring course_id is set as it's part of the uniqueness key
    tt1 = TeeTime(date="2024-08-01", time="10:00", course_id=1, players=2, price=50)
    tt2 = TeeTime(date="2024-08-01", time="10:00", course_id=1, players=4, price=55) # Duplicate of tt1
    tt3 = TeeTime(date="2024-08-01", time="11:00", course_id=1, players=3, price=60) # Unique time
    tt4 = TeeTime(date="2024-08-01", time="10:00", course_id=2, players=2, price=50) # Unique course_id
    tt5 = TeeTime(date="2024-08-02", time="10:00", course_id=1, players=2, price=50) # Unique date

    input_tee_times = [tt1, tt2, tt3, tt4, tt5]
    deduped_list = aggregate_and_deduplicate_tee_times(input_tee_times)

    assert len(deduped_list) == 4 # tt2 should be removed
    
    # Create a list of tuples for easier comparison, as model instances won't be identical
    # if __eq__ is not defined to compare by values.
    # The key for uniqueness is (date, time, course_id)
    expected_unique_keys = {
        ("2024-08-01", "10:00", 1), # tt1 (tt2 is a duplicate of this)
        ("2024-08-01", "11:00", 1), # tt3
        ("2024-08-01", "10:00", 2), # tt4
        ("2024-08-02", "10:00", 1)  # tt5
    }
    
    output_keys = {(tt.date, tt.time, tt.course_id) for tt in deduped_list}
    assert output_keys == expected_unique_keys

    # Check that the first encountered version of a duplicate is kept (tt1, not tt2)
    # This depends on the stability of the loop and list processing in the function.
    # The current implementation naturally keeps the first one encountered.
    kept_tt1_equivalent = next(tt for tt in deduped_list if tt.date == "2024-08-01" and tt.time == "10:00" and tt.course_id == 1)
    assert kept_tt1_equivalent.players == 2 # tt1's player count
    assert kept_tt1_equivalent.price == 50 # tt1's price


@patch("src.services.scraping_service.db_insert_courses")
@patch("src.services.scraping_service.db_get_courses_by_resort")
@patch("src.services.scraping_service.fetch_bally_tee_times") # Example fetcher
@patch("src.services.scraping_service.scrape_bally_tee_times") # Example scraper
@patch("src.services.scraping_service.fetch_pippy_tee_times") 
@patch("src.services.scraping_service.scrape_pippy_tee_times")
@patch("src.services.scraping_service.fetch_glendenning_tee_times")
@patch("src.services.scraping_service.scrape_glendenning_tee_times")
@patch("src.services.scraping_service.fetch_wilds_tee_times")
@patch("src.services.scraping_service.scrape_wilds_tee_times")
@patch("src.services.scraping_service.aggregate_and_deduplicate_tee_times") # Mock this too
@patch("src.services.scraping_service.db_insert_tee_times")
def test_run_scheduled_scrape_logic(
    mock_db_insert_tee_times,
    mock_aggregate_deduplicate,
    mock_scrape_wilds, mock_fetch_wilds, # Order matters for mock objects if not named
    mock_scrape_glendenning, mock_fetch_glendenning,
    mock_scrape_pippy, mock_fetch_pippy,
    mock_scrape_bally, mock_fetch_bally,
    mock_db_get_courses_by_resort,
    mock_db_insert_courses,
    db_session_test: Session # Use the actual test session
):
    scrape_date = "2024-08-10"

    # --- Mock Configurations ---
    # Mock db_get_courses_by_resort to return specific courses for each resort type
    # These Course objects need 'id' and other attributes used by the service.
    # The SERVICE_COURSES from scraping_service.py are used by db_insert_courses,
    # so we can simulate that they've been inserted and given IDs.
    
    # Simulate that courses have IDs after insertion
    mock_bally_course = Course(id=1, value="Championship SOUTH", label="Championship-SOUTH", resort="Bally Haly", holes=18, url="...")
    mock_pippy_course = Course(id=2, value="Admirals Green", label="ADMIRALS_GREEN", resort="Pippy Park", holes=18, url="...")
    mock_glendenning_course = Course(id=3, value="Glendenning", label="GLEDENNING", resort="Glendenning", holes=18, url="...")
    mock_wilds_course = Course(id=4, value="The Wilds", label="THE_WILDS", resort="The Wilds", holes=18, url="...")

    def get_courses_side_effect(resort_name, db_session):
        if resort_name == "Bally Haly":
            return [mock_bally_course]
        if resort_name == "Pippy Park":
            return [mock_pippy_course]
        if resort_name == "Glendenning":
            return [mock_glendenning_course]
        if resort_name == "The Wilds":
            return [mock_wilds_course]
        return []
    mock_db_get_courses_by_resort.side_effect = get_courses_side_effect

    # Mock fetch and scrape functions to return some dummy data
    mock_fetch_bally.return_value = "raw_bally_data"
    mock_scrape_bally.return_value = [TeeTime(course_id=1, date=scrape_date, time="10:00", players=2, price=50)]
    
    mock_fetch_pippy.return_value = "raw_pippy_data"
    mock_scrape_pippy.return_value = [TeeTime(course_id=2, date=scrape_date, time="11:00", players=3, price=60)]

    mock_fetch_glendenning.return_value = "raw_glendenning_data"
    mock_scrape_glendenning.return_value = [] # Simulate no tee times found

    mock_fetch_wilds.return_value = "raw_wilds_data"
    mock_scrape_wilds.return_value = [TeeTime(course_id=4, date=scrape_date, time="12:00", players=4, price=70)]

    # Mock aggregate_and_deduplicate_tee_times to return its input directly or a known list
    # The important part is that it's called with the combined list of scraped tee times.
    # Let's say it returns a list of 3 unique tee times (Bally, Pippy, Wilds)
    final_deduped_list = [
        TeeTime(course_id=1, date=scrape_date, time="10:00", players=2, price=50),
        TeeTime(course_id=2, date=scrape_date, time="11:00", players=3, price=60),
        TeeTime(course_id=4, date=scrape_date, time="12:00", players=4, price=70)
    ]
    mock_aggregate_deduplicate.return_value = final_deduped_list
    
    # --- Call the service function ---
    run_scheduled_scrape(db=db_session_test, scrape_date=scrape_date)

    # --- Assertions ---
    # 1. db_insert_courses was called with the SERVICE_COURSES constant and the session
    mock_db_insert_courses.assert_called_once_with(SERVICE_COURSES, db_session_test)

    # 2. db_get_courses_by_resort was called for each resort type
    expected_resort_calls = [
        call("Bally Haly", db_session_test),
        call("Pippy Park", db_session_test),
        call("Glendenning", db_session_test),
        call("The Wilds", db_session_test)
    ]
    mock_db_get_courses_by_resort.assert_has_calls(expected_resort_calls, any_order=True) # any_order True because dict iteration order isn't guaranteed for older Python

    # 3. Fetch and scrape functions were called for each course that was "found"
    mock_fetch_bally.assert_called_once_with(scrape_date, mock_bally_course)
    mock_scrape_bally.assert_called_once_with("raw_bally_data", mock_bally_course, scrape_date)

    mock_fetch_pippy.assert_called_once_with(scrape_date, mock_pippy_course)
    mock_scrape_pippy.assert_called_once_with("raw_pippy_data", mock_pippy_course, scrape_date)
    
    mock_fetch_glendenning.assert_called_once_with(scrape_date, mock_glendenning_course)
    mock_scrape_glendenning.assert_called_once_with("raw_glendenning_data", mock_glendenning_course, scrape_date)

    mock_fetch_wilds.assert_called_once_with(scrape_date, mock_wilds_course)
    mock_scrape_wilds.assert_called_once_with("raw_wilds_data", mock_wilds_course, scrape_date)

    # 4. aggregate_and_deduplicate_tee_times was called with all scraped tee times
    # The expected list passed to aggregate should be the concatenation of scrape_*.return_value
    # where course_id is correctly set. The mock_scrape_*.return_value already has course_id.
    expected_aggregate_input = (
        mock_scrape_bally.return_value + 
        mock_scrape_pippy.return_value + 
        mock_scrape_glendenning.return_value + # This is an empty list in our mock
        mock_scrape_wilds.return_value
    )
    # The TeeTime objects in the actual call will have their course_id field populated by the service logic.
    # The mock_scrape_*.return_value should reflect this.
    # Let's verify the content of the list passed to mock_aggregate_deduplicate.
    # The call object is mock_aggregate_deduplicate.call_args[0][0]
    actual_aggregate_input = mock_aggregate_deduplicate.call_args[0][0]
    
    # Compare elements carefully, as list of objects might not compare directly if objects are different instances.
    assert len(actual_aggregate_input) == len(expected_aggregate_input)
    # For a more robust check, compare key attributes of each TeeTime
    for actual_tt, expected_tt in zip(sorted(actual_aggregate_input, key=lambda x: x.course_id), sorted(expected_aggregate_input, key=lambda x: x.course_id)):
        assert actual_tt.course_id == expected_tt.course_id
        assert actual_tt.date == expected_tt.date
        assert actual_tt.time == expected_tt.time
        assert actual_tt.players == expected_tt.players
        assert actual_tt.price == expected_tt.price


    # 5. db_insert_tee_times was called with the result from aggregate_and_deduplicate_tee_times
    mock_db_insert_tee_times.assert_called_once_with(final_deduped_list, db_session_test)


def test_run_scheduled_scrape_no_courses_found(
    mock_db_insert_tee_times: MagicMock, # Need to pass these to the decorator
    mock_aggregate_deduplicate: MagicMock,
    mock_scrape_wilds: MagicMock, mock_fetch_wilds: MagicMock,
    mock_scrape_glendenning: MagicMock, mock_fetch_glendenning: MagicMock,
    mock_scrape_pippy: MagicMock, mock_fetch_pippy: MagicMock,
    mock_scrape_bally: MagicMock, mock_fetch_bally: MagicMock,
    mock_db_get_courses_by_resort: MagicMock,
    mock_db_insert_courses: MagicMock,
    db_session_test: Session
):
    scrape_date = "2024-08-11"
    mock_db_get_courses_by_resort.return_value = [] # Simulate no courses found for any resort

    run_scheduled_scrape(db=db_session_test, scrape_date=scrape_date)

    mock_db_insert_courses.assert_called_once_with(SERVICE_COURSES, db_session_test)
    
    # Fetch/scrape functions should not be called if no courses
    mock_fetch_bally.assert_not_called()
    mock_scrape_bally.assert_not_called()
    mock_fetch_pippy.assert_not_called()
    # ... and so on for other scrapers

    # Aggregate should be called with an empty list
    mock_aggregate_deduplicate.assert_called_once_with([])
    
    # Insert tee times should be called with the result of aggregation (empty list)
    # or not called at all if there's a guard for empty list.
    # Current implementation of run_scheduled_scrape:
    # if deduped_tee_times: db_insert_tee_times(...) else: print("No new unique tee times to insert.")
    # So, if aggregate returns empty list, insert_tee_times should not be called.
    mock_db_insert_tee_times.assert_not_called() # Assuming aggregate returns empty list
    
    # If aggregate itself returns an empty list:
    mock_aggregate_deduplicate.return_value = []
    run_scheduled_scrape(db=db_session_test, scrape_date=scrape_date) # Call again with this condition
    mock_db_insert_tee_times.assert_not_called() # Verify this path too
