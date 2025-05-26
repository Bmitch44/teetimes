from sqlmodel import SQLModel, Field, create_engine, Session, select

from src.courses.bally_haly import fetch_bally_tee_times, scrape_bally_tee_times
from src.courses.glendenning import fetch_glendenning_tee_times, scrape_glendenning_tee_times
from src.courses.pippy_park import fetch_pippy_tee_times, scrape_pippy_tee_times
from src.courses.wilds import fetch_wilds_tee_times, scrape_wilds_tee_times

from src.models import Course, TeeTime

# Create DB
engine = create_engine("sqlite:///teetimes.db")
SQLModel.metadata.create_all(engine)

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
        # Use a tuple of (date, time, course) as the unique key
        key = (tee_time.date, tee_time.time, tee_time.course)
        if key not in seen:
            seen.add(key)
            deduped.append(tee_time)
    return deduped

def insert_tee_times(tee_times: list[TeeTime]):
    try:
        with Session(engine) as session:
            for tee_time in tee_times:
                existing = session.exec(
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
                    session.add(tee_time)
            session.commit()
    except Exception as e:
        session.rollback()
        print(e)

def insert_courses(courses: list[Course]):
    try:
        with Session(engine) as session:
            for course in courses:
                existing = session.exec(
                    select(Course).where(Course.value == course.value)
                ).first()
                if existing:
                    existing.label = course.label
                    # Add more fields if needed
                else:
                    session.add(course)
            session.commit()
    except Exception as e:
        session.rollback()
        print(e)

def get_course_by_id(course_id: int) -> Course:
    with Session(engine) as session:
        return session.exec(select(Course).where(Course.id == course_id)).first()
    
def get_courses_by_resort(resort: str) -> list[Course]:
    with Session(engine) as session:
        return session.exec(select(Course).where(Course.resort == resort)).all()

def get_all_courses() -> list[Course]:
    with Session(engine) as session:
        return session.exec(select(Course)).all()

def main():
    bally_url = "https://ballyhalygolf.totaleintegrated.com/Public-Tee-Times"
    EXECUTIVE_NORTH = "Executive-NORTH"
    CHAMPIONSHIP_SOUTH = "Championship-SOUTH"

    pippy_url = "https://www.pippypark.com/what-to-do/golfing/"
    ADMIRALS_GREEN = "ADMIRALS_GREEN"
    CAPTAINS_HILL = "CAPTAINS_HILL"

    insert_courses(COURSES)

    bally_courses = get_courses_by_resort("Bally Haly")
    pippy_courses = get_courses_by_resort("Pippy Park")
    glendenning_courses = get_courses_by_resort("Glendenning")
    wilds_courses = get_courses_by_resort("The Wilds")
    for course in bally_courses:
        results = fetch_bally_tee_times("2025-05-23", course)
        tee_times = scrape_bally_tee_times(results, course, "2025-05-23")
        deduped_tee_times = aggregate_and_deduplicate_tee_times(tee_times)
        insert_tee_times(deduped_tee_times)

    for course in pippy_courses:
        results = fetch_pippy_tee_times("2025-05-23", course)
        tee_times = scrape_pippy_tee_times(results, course, "2025-05-23")
        deduped_tee_times = aggregate_and_deduplicate_tee_times(tee_times)
        insert_tee_times(deduped_tee_times)

    for course in glendenning_courses:
        results = fetch_glendenning_tee_times("2025-05-23", course)
        tee_times = scrape_glendenning_tee_times(results, course, "2025-05-23")
        deduped_tee_times = aggregate_and_deduplicate_tee_times(tee_times)
        insert_tee_times(deduped_tee_times)

    for course in wilds_courses:
        results = fetch_wilds_tee_times("2025-05-23", course)
        tee_times = scrape_wilds_tee_times(results, course, "2025-05-23")
        deduped_tee_times = aggregate_and_deduplicate_tee_times(tee_times)
        insert_tee_times(deduped_tee_times)

if __name__ == "__main__":
    import time
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"\n\nTotal Time taken: {end_time - start_time:.2f} seconds\n")
