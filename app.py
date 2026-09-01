import os

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, render_template, request
from werkzeug.security import generate_password_hash

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


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            "",
        ).strip()

        email = request.form.get(
            "email",
            "",
        ).strip().lower()

        password = request.form.get(
            "password",
            "",
        )

        confirm_password = request.form.get(
            "confirm_password",
            "",
        )

        if not name:

            return render_template(
                "register.html",
                message="Name is required.",
                name=name,
                email=email,
            )

        if not email:

            return render_template(
                "register.html",
                message="Email is required.",
                name=name,
                email=email,
            )

        if not password:

            return render_template(
                "register.html",
                message="Password is required.",
                name=name,
                email=email,
            )

        if len(password) < 6:

            return render_template(
                "register.html",
                message=(
                    "Password must contain at least "
                    "6 characters."
                ),
                name=name,
                email=email,
            )

        if password != confirm_password:

            return render_template(
                "register.html",
                message="Passwords do not match.",
                name=name,
                email=email,
            )

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s
            """,
            (email,),
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()

            return render_template(
                "register.html",
                message="This email is already registered.",
                name=name,
                email=email,
            )

        password_hash = generate_password_hash(
            password
        )

        cursor.execute(
            """
            INSERT INTO users (
                name,
                email,
                password_hash
            )
            VALUES (%s, %s, %s)
            """,
            (
                name,
                email,
                password_hash,
            ),
        )

        db.commit()
        cursor.close()

        return render_template(
            "register.html",
            message=(
                "Account created successfully. "
                "You can now log in."
            ),
            success=True,
        )

    return render_template("register.html")


# Start the Flask development server
if __name__ == "__main__":
    app.run(debug=True)