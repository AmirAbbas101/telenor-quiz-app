from flask import Flask, jsonify, render_template
import requests
from bs4 import BeautifulSoup
from werkzeug.exceptions import HTTPException
import datetime
import os
import time

# Initialize Flask app
app = Flask(__name__)

# Set the timezone
os.environ["TZ"] = "Asia/Karachi"
time.tzset()

# Logging timezone setup
app.logger.info(f"Timezone set to: {time.tzname}")

# Global variables for quiz data and update tracking
quiz_data = {}
last_update_date = None


def get_current_date():
    """Returns the current date in UTC."""
    return datetime.datetime.utcnow()


def is_data_outdated():
    """Checks if the stored quiz data is outdated."""
    global last_update_date
    current_date = get_current_date()
    return last_update_date is None or last_update_date.day != current_date.day


def fetch_webpage(url):
    """Fetches and returns the HTML content of the given URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        app.logger.error(f"Failed to fetch the webpage. Error: {str(e)}")
        return None


def parse_quiz_data(html):
    """Parses quiz data from the provided HTML content."""
    soup = BeautifulSoup(html, "html.parser")

    # Extract quiz date
    quiz_date_heading = soup.find("h2", class_="wp-block-heading")
    quiz_date = (
        quiz_date_heading.get_text(strip=True) if quiz_date_heading else "Unknown Date"
    )

    # Extract questions and answers
    questions = []
    question_blocks = soup.find_all("h4", class_="wp-block-heading")
    for question_block in question_blocks:
        question_text = question_block.get_text(strip=True)
        answer_paragraph = question_block.find_next("p")
        answer = (
            answer_paragraph.find("strong").get_text(strip=True)
            if answer_paragraph and answer_paragraph.find("strong")
            else "No answer provided"
        )
        questions.append({"question": question_text, "answer": answer})

    return {
        "quiz_date": quiz_date,
        "questions": questions,
    }


def scrape_quiz_data():
    """Scrapes quiz data from the source website."""
    url = "https://urdohi.com/my-telenor-test-your-skills/"
    html_content = fetch_webpage(url)
    if not html_content:
        return {"message": "Failed to fetch quiz data."}

    global quiz_data, last_update_date
    quiz_data = parse_quiz_data(html_content)
    last_update_date = get_current_date()
    app.logger.info("Quiz data successfully scraped and updated.")
    return quiz_data


@app.route("/", methods=["GET"])
def get_quiz_data():
    """Renders the quiz data on the home page."""
    if is_data_outdated():
        scrape_quiz_data()
    return render_template("index.html", quiz_data=quiz_data)


@app.route("/api/quiz/", methods=["GET"])
def quiz_api():
    """Provides quiz data in JSON format via API."""
    if is_data_outdated():
        scrape_quiz_data()
    return jsonify(quiz_data), 200


@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """Handles HTTP exceptions gracefully."""
    return jsonify({"error": e.description}), e.code


@app.errorhandler(Exception)
def handle_general_exception(e):
    """Handles unexpected errors."""
    app.logger.error(f"Unexpected error: {str(e)}")
    return jsonify({"error": "An unexpected error occurred."}), 500


if __name__ == "__main__":
    # Run the Flask application
    app.run(host="0.0.0.0", port=5000, debug=False)
