import time as t

from selectolax.parser import HTMLParser
from playwright.sync_api import sync_playwright

from src.models.course import Course
from src.models.tee_time import TeeTime


def scrape_wilds_tee_times(html, course: Course, date: str) -> list[TeeTime]:
    start_time = t.time()
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
    end_time = t.time()
    print(f"Time taken: {end_time - start_time:.2f} seconds\n")
    return tee_times

def fetch_wilds_tee_times(date_str, course: Course):
    start_time = t.time()
    print(f"Fetching tee times for {course.label} on {date_str}")
    url = "https://www.tee-on.com/PubGolf/servlet/com.teeon.teesheet.servlets.golfersection.WebBookingAllTimesLanding?CourseCode=SMRV&Referrer=thewilds.ca"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(2000)

        page.click(f'a.search-results-date[id="{date_str}"]')
        page.wait_for_timeout(2000)

        page.click('a#hole-filter-18')
        page.wait_for_timeout(2000)

        end_time = t.time()
        print(f"Time taken: {end_time - start_time:.2f} seconds\n")
        return page.content()

