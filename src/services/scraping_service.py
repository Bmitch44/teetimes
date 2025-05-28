from sqlmodel import Session
# Adjusted imports to use functions from src.db and pass the session
from src.db import get_session, insert_courses as db_insert_courses, insert_tee_times as db_insert_tee_times, get_courses_by_resort as db_get_courses_by_resort
from src.models import Course, TeeTime # Assuming models are directly in src.models

# Import course-specific scraping functions
from src.courses.bally_haly import fetch_bally_tee_times, scrape_bally_tee_times
from src.courses.glendenning import fetch_glendenning_tee_times, scrape_glendenning_tee_times
from src.courses.pippy_park import fetch_pippy_tee_times, scrape_pippy_tee_times
from src.courses.wilds import fetch_wilds_tee_times, scrape_wilds_tee_times

# COURSES constant from old_main.py
COURSES = [
    Course(value="Championship SOUTH", label="Championship-SOUTH", resort="Bally Haly", holes=18, url="https://ballyhalygolf.totaleintegrated.com/Public-Tee-Times"),
    Course(value="Executive NORTH", label="Executive-NORTH", resort="Bally Haly", holes=18, url="https://ballyhalygolf.totaleintegrated.com/Public-Tee-Times"),
    Course(value="Admirals Green", label="ADMIRALS_GREEN", resort="Pippy Park", holes=18, url="https://www.tee-on.com/PubGolf/servlet/com.teeon.teesheet.servlets.golfersection.WebBookingAllTimesLanding?CourseGroupID=11757&CourseCode=ADMI&LoginType=5&BackTarget=com.teeon.teesheet.servlets.golfersection.ComboLanding&Referrer=www.pippypark.com"),
    Course(value="Admirals Green 9 Hole", label="ADMIRALS_GREEN_9", resort="Pippy Park", holes=9, url="https://www.tee-on.com/PubGolf/servlet/com.teeon.teesheet.servlets.golfersection.WebBookingAllTimesLanding?CourseGroupID=11757&CourseCode=ADMI&LoginType=5&BackTarget=com.teeon.teesheet.servlets.golfersection.ComboLanding&Referrer=www.pippypark.com"),
    Course(value="Captains Hill", label="CAPTAINS_HILL", resort="Pippy Park", holes=18, url="https://www.tee-on.com/PubGolf/servlet/com.teeon.teesheet.servlets.golfersection.WebBookingAllTimesLanding?CourseGroupID=11758&CourseCode=CAPT&LoginType=5&BackTarget=com.teeon.teesheet.servlets.golfersection.ComboLanding&Referrer=www.pippypark.com"),
    Course(value="Glendenning", label="GLEDENNING", resort="Glendenning", holes=18, url="https://www.tee-on.com/PubGolf/servlet/com.teeon.teesheet.servlets.golfersection.WebBookingAllTimesLanding?CourseCode=GGGG&Referrer="),
    Course(value="The Wilds", label="THE_WILDS", resort="The Wilds", holes=18, url="https://www.tee-on.com/PubGolf/servlet/com.teeon.teesheet.servlets.golfersection.WebBookingAllTimesLanding?CourseCode=SMRV&Referrer=thewilds.ca"),
    Course(value="The Wilds 9 Hole", label="THE_WILDS_9", resort="The Wilds", holes=9, url="https://www.tee-on.com/PubGolf/servlet/com.teeon.teesheet.servlets.golfersection.WebBookingAllTimesLanding?CourseCode=SMRV&Referrer=thewilds.ca"),
]

def aggregate_and_deduplicate_tee_times(results: list[TeeTime]) -> list[TeeTime]:
    seen = set()
    deduped = []
    for tee_time in results:
        # Use a tuple of (date, time, course_id) as the unique key
        # Assuming course_id is populated correctly before this function is called
        key = (tee_time.date, tee_time.time, tee_time.course_id)
        if key not in seen:
            seen.add(key)
            deduped.append(tee_time)
    return deduped

def run_scheduled_scrape(db: Session, scrape_date: str = "2025-05-23"): # Accepts a DB session and a date
    """
    Runs the scraping process for all configured courses and updates the database.
    The scrape_date parameter is for demonstration; in a real scenario,
    this would likely be the current date or a configurable date range.
    """
    print(f"Scraping and database update process started for date: {scrape_date}")

    # Insert course definitions into the database
    # This ensures courses are present before tee times are linked to them.
    # In a real app, this might be a one-time setup or managed differently.
    db_insert_courses(COURSES, db)
    print(f"Inserted/Updated {len(COURSES)} courses in the database.")

    all_scraped_tee_times = []

    course_scraper_map = {
        "Bally Haly": (fetch_bally_tee_times, scrape_bally_tee_times),
        "Pippy Park": (fetch_pippy_tee_times, scrape_pippy_tee_times),
        "Glendenning": (fetch_glendenning_tee_times, scrape_glendenning_tee_times),
        "The Wilds": (fetch_wilds_tee_times, scrape_wilds_tee_times),
    }

    for resort_name, (fetch_func, scrape_func) in course_scraper_map.items():
        print(f"Processing resort: {resort_name}")
        courses_in_resort = db_get_courses_by_resort(resort_name, db)
        if not courses_in_resort:
            print(f"No courses found for resort: {resort_name}. Skipping.")
            continue
        
        for course in courses_in_resort:
            print(f"Fetching and scraping for course: {course.label} ({course.value})")
            try:
                # Ensure course.id is available for linking TeeTime.course_id
                if course.id is None:
                    # This should ideally not happen if courses are inserted first and IDs populated
                    print(f"Warning: Course ID is None for {course.label}. Tee times may not link correctly.")
                
                raw_data = fetch_func(scrape_date, course) # Pass date and course object
                # Scrape functions need to be adapted if they expect different params or if course_id needs to be set
                tee_times = scrape_func(raw_data, course, scrape_date) # Pass date and course object
                
                # Ensure course_id is set on each tee_time if not already done by scrape_func
                for tt in tee_times:
                    tt.course_id = course.id

                all_scraped_tee_times.extend(tee_times)
                print(f"Found {len(tee_times)} tee times for {course.label}.")
            except Exception as e:
                print(f"Error scraping {course.label}: {e}")

    if not all_scraped_tee_times:
        print("No tee times were scraped across all courses.")
    else:
        print(f"Total tee times scraped before deduplication: {len(all_scraped_tee_times)}")
        deduped_tee_times = aggregate_and_deduplicate_tee_times(all_scraped_tee_times)
        print(f"Total tee times after deduplication: {len(deduped_tee_times)}")
        
        if deduped_tee_times:
            db_insert_tee_times(deduped_tee_times, db)
            print(f"Successfully inserted/updated {len(deduped_tee_times)} tee times in the database.")
        else:
            print("No new unique tee times to insert.")

    print(f"Scraping and database update process completed for date: {scrape_date}")

# Example of how to run this service (e.g., for a scheduled job or CLI command)
# if __name__ == "__main__":
#     import time
#     from src.db import create_db_and_tables
# 
#     print("Initializing database...")
#     create_db_and_tables() # Ensure DB is ready
# 
#     start_time = time.time()
#     # Get a new session for the scrape
#     db_session_generator = get_session()
#     db = next(db_session_generator)
#     try:
#         run_scheduled_scrape(db=db, scrape_date="2025-07-01") # Example date
#     finally:
#         db.close() # Ensure session is closed
#     end_time = time.time()
#     print(f"\n\nTotal Time taken for scrape: {end_time - start_time:.2f} seconds\n")
