"""
Bally Haly Golf Club
"""
import time as t
from selectolax.parser import HTMLParser
from playwright.sync_api import sync_playwright
import datetime

from src.models.course import Course
from src.models.tee_time import TeeTime

def scrape_bally_tee_times(htmls, course: Course, date: str):
    start_time = t.time()
    print(f"Scraping tee times for {course.label} on {date}")
    tee_times = []
    for html in htmls:
        tree = HTMLParser(html)
        parent = tree.css_first('span#dnn_ctr3529_DefaultView_ctl01_dlTeeTimes')
        if not parent:
            return []

        for block in parent.css('span.TeeBlock'):

            # Time
            time_node = block.css_first('div.time > span')
            time = time_node.text(strip=True) if time_node else None

            # Course, price (from the first table inside the block)
            table = block.css_first('table')
            if table:
                tds = table.css('td')
                if len(tds) >= 3:
                    price = tds[5].text(strip=True)

            # Players (available spots)
            players = None
            select = block.css_first('select#ddlNumPlayers')
            if select:
                options = select.css('option')
                max_players = options[1].text(strip=True)
                if options:
                    # The last option value is the max number of players
                    try:
                        players = int(max_players)
                    except ValueError:
                        players = None

            tee_time = TeeTime(
                date=date,
                time=time,
                course_id=course.id,
                price=price.split("/")[0],
                players=players,
                holes=course.holes
            )
            tee_times.append(tee_time)

    end_time = t.time()
    print(f"Time taken: {end_time - start_time:.2f} seconds\n")
    return tee_times

def fetch_bally_tee_times(date_str, course: Course):
    start_time = t.time()
    print(f"Fetching tee times for {course.label} on {date_str}")
    url = "https://ballyhalygolf.totaleintegrated.com/Public-Tee-Times"
    search_times = [
        "05:00 AM", "07:00 AM", "10:00 AM", "01:00 PM", "03:00 PM", "06:00 PM"
    ]
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)

        # Select the course
        page.select_option('select#dnn_ctr3529_DefaultView_ctl01_cmbCourse', label=course.label)
        with page.expect_response(lambda response: response.request.method == "POST" and "/Public-Tee-Times" in response.url):
            page.click('body', position={'x': 0, 'y': 0})
        page.wait_for_timeout(1000)

        # Open the calendar and select the date
        page.click('input[name="dnn$ctr3529$DefaultView$ctl01$Calendar$dateInput"]')
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        title = dt.strftime("%A, %B %-d, %Y")
        with page.expect_response(lambda response: response.request.method == "POST" and "/Public-Tee-Times" in response.url):
            page.click(f'td[title="{title}"] a')
        page.wait_for_timeout(1000)  # Wait for DOM update

        for time_str in search_times:
            # Select the time in the dropdown
            page.select_option('select#dnn_ctr3529_DefaultView_ctl01_cmbHour', label=time_str)
            # Wait for the POST request after selecting the time
            with page.expect_response(lambda response: response.request.method == "POST" and "/Public-Tee-Times" in response.url):
                page.click('body', position={'x': 0, 'y': 0}) # Click outside to close dropdown and trigger event if needed
            page.wait_for_timeout(1000)  # Wait for DOM update
            html = page.content()
            results.append(html)

        browser.close()
    end_time = t.time()
    print(f"Time taken: {end_time - start_time:.2f} seconds\n")
    return results