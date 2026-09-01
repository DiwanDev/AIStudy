import os

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, render_template


# Load values from the .env file
load_dotenv()


# Create the Flask application
app = Flask(__name__)


# Connect Flask/Python to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password=os.getenv("MYSQL_PASSWORD"),
    database="aistudy_db",
)


# Confirm the database connection in the terminal
if db.is_connected():
    app.logger.info(
        "Connected to AIStudy MySQL database!"
    )


# Home-page route
@app.route("/")
def home():

    return render_template("home.html")


# Database-test route
@app.route("/test-db")
def test_db():

    # Create a cursor for executing SQL
    cursor = db.cursor()

    # Ask MySQL for the currently selected database
    cursor.execute(
        """
        SELECT DATABASE()
        """
    )

    # Get one result
    result = cursor.fetchone()

    # Close the cursor
    cursor.close()

    # Display the database name in the browser
    return (
        "Successfully connected to database: "
        + result[0]
    )


# Start the Flask development server
if __name__ == "__main__":
    app.run(debug=True)