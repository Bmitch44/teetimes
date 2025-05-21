

from selectolax.parser import HTMLParser
from playwright.sync_api import sync_playwright

from src.models.course import Course
from src.models.tee_time import TeeTime


def scrape_pippy_tee_times(html, course: Course, date: str) -> list[TeeTime]:
    print(f"Scraping tee times for {course.label} on {date}")
    tree = HTMLParser(html)
    parent = tree.css_first('div.search-results-tee-times-wrapper')
    if not parent:
        return []

    tee_times = []
    for block in tree.css('div.search-results-tee-times-box'):
        time_node = block.css_first('p.time')
        time = time_node.text(strip=True) if time_node else None

        price_node = block.css_first('p.price')
        price = price_node.text(strip=True) if price_node else None

        players_node = block.css_first('div.players-allowed')
        players = players_node.text(strip=True) if players_node else None

        if time and price and players:
            tee_times.append(
                TeeTime(
                    time=time,
                    price=price,
                    players=int(players.split(" ")[-2]),
                    date=date,
                    course_id=course.id
                )
            )
                    
    return tee_times

def fetch_pippy_tee_times(date_str, course: Course):
    print(f"Fetching tee times for {course.label} on {date_str}")
    COURSES = {
        "ADMIRALS_GREEN": "https://www.tee-on.com/PubGolf/servlet/com.teeon.teesheet.servlets.golfersection.WebBookingAllTimesLanding?CourseGroupID=11757&CourseCode=ADMI&LoginType=5&BackTarget=com.teeon.teesheet.servlets.golfersection.ComboLanding&Referrer=www.pippypark.com",
        "CAPTAINS_HILL": "https://www.tee-on.com/PubGolf/servlet/com.teeon.teesheet.servlets.golfersection.WebBookingAllTimesLanding?CourseGroupID=11758&CourseCode=CAPT&LoginType=5&BackTarget=com.teeon.teesheet.servlets.golfersection.ComboLanding&Referrer=www.pippypark.com"
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(COURSES[course.label])
        page.wait_for_timeout(2000)

        if course.label == "ADMIRALS_GREEN":
            page.click('a#popupMessagesClose')
            page.wait_for_timeout(4000)

        page.click(f'a.search-results-date[id="{date_str}"]')
        page.wait_for_timeout(2000)

        if course.label == "ADMIRALS_GREEN":
            page.click('a#popupMessagesClose')
            page.wait_for_timeout(2000)

        return page.content()
