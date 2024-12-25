from flask import Flask, jsonify, render_template
import requests
from bs4 import BeautifulSoup
from werkzeug.exceptions import HTTPException
import datetime
import os
import time

# Initialize Flask app
app = Flask(__name__)

# Ensure the timezone is consistent
os.environ["TZ"] = "Asia/Karachi"
time.tzset()

# Log the current timezone
app.logger.info(f"Timezone set to: {time.tzname}")

data = {}
day = 1


# Function to scrape quiz data from the given URL
def scrape_quiz_data():
    try:
        url = "https://urdohi.com/my-telenor-test-your-skills/"
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
    except requests.RequestException as e:
        app.logger.error(f"Failed to fetch the webpage. Error: {str(e)}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    quiz_date_heading = soup.find("h2", class_="wp-block-heading")
    quiz_date = (
        quiz_date_heading.get_text(strip=True) if quiz_date_heading else "Unknown Date"
    )

    questions = []
    question_blocks = soup.find_all("h4", class_="wp-block-heading")

    for question_block in question_blocks:
        question_text = question_block.get_text(strip=True)

        answer_paragraph = question_block.find_next("p")
        answer = ""
        if answer_paragraph and answer_paragraph.find("strong"):
            answer = answer_paragraph.find("strong").get_text(strip=True)

        questions.append({"question": question_text, "answer": answer})

    current_date = datetime.datetime.utcnow()
    quiz_date = f"{current_date.month}/{current_date.day}/{current_date.year}"
    # del questions[0]
    global data
    global day
    day = current_date.day
    print(day)
    data = {"quiz_date": quiz_date, "questions": questions}
    app.logger.info("Quiz data successfully scraped and updated.")


# Route to render quiz data on the home page
@app.route("/", methods=["GET"])
def get_quiz_data():
    # Call scrape_quiz_data manually when the route is accessed
    current_date = datetime.datetime.utcnow()
    if day != current_date.day:
        scrape_quiz_data()
    if not data:
        return render_template(
            "index.html", quiz_data={"message": "Quiz data is not available yet."}
        )
    return render_template("index.html", quiz_data=data)


# API route to retrieve quiz data in JSON format
@app.route("/api/quiz/", methods=["GET"])
def quiz_api():
    scrape_quiz_data()
    if not data:
        return jsonify({"message": "Quiz data is not available yet."}), 200
    return jsonify(data), 200


# Error handling
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return jsonify({"error": e.description}), e.code


@app.errorhandler(Exception)
def handle_general_exception(e):
    app.logger.error(f"Unexpected error: {str(e)}")
    return jsonify({"error": "An unexpected error occurred."}), 500


if __name__ == "__main__":
    # Start the Flask application
    app.run(host="0.0.0.0", port=5000, debug=False)
