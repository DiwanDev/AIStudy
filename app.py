import os
import uuid

import mysql.connector
from dotenv import load_dotenv

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from werkzeug.utils import secure_filename
# Load values from the .env file
load_dotenv()


# Create the Flask application
app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")


if not app.secret_key:
    raise RuntimeError(
        "SECRET_KEY is missing from the .env file."
    )


app.config["UPLOAD_FOLDER"] = os.path.join(
    app.root_path,
    "uploads",
)

app.config["MAX_CONTENT_LENGTH"] = (
    10 * 1024 * 1024
)


os.makedirs(
    app.config["UPLOAD_FOLDER"],
    exist_ok=True,
)
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
# File extensions accepted by AIStudy
ALLOWED_EXTENSIONS = {
    "pdf",
    "txt",
}


# Check whether an uploaded file has an allowed extension
def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )

# Home-page route
@app.route("/")
def home():

    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get(
            "email",
            "",
        ).strip().lower()

        password = request.form.get(
            "password",
            "",
        )

        if not email or not password:

            return render_template(
                "login.html",
                message="Email and password are required.",
                email=email,
            )

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                password_hash
            FROM users
            WHERE email = %s
            """,
            (email,),
        )

        user = cursor.fetchone()

        cursor.close()

        if user and check_password_hash(
            user["password_hash"],
            password,
        ):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            message="Invalid email or password.",
            email=email,
        )

    return render_template("login.html")
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            id,
            name,
            email,
            created_at
        FROM users
        WHERE id = %s
        """,
        (session["user_id"],),
    )

    user = cursor.fetchone()

    cursor.close()

    if user is None:

        session.clear()

        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        user=user,
    )
@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return redirect(url_for("home"))
@app.route(
    "/documents",
    methods=["GET", "POST"],
)
def documents():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    message = None
    success = False

    if request.method == "POST":

        uploaded_file = request.files.get(
            "document"
        )

        if not uploaded_file:

            message = "Please choose a file."

        elif uploaded_file.filename == "":

            message = "Please choose a file."

        elif not allowed_file(
            uploaded_file.filename
        ):

            message = (
                "Only PDF and TXT files are allowed."
            )

        else:

            original_filename = secure_filename(
                uploaded_file.filename
            )

            extension = original_filename.rsplit(
                ".",
                1,
            )[1].lower()

            stored_filename = (
                uuid.uuid4().hex
                + "."
                + extension
            )

            file_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                stored_filename,
            )

            uploaded_file.save(
                file_path
            )

            file_size = os.path.getsize(
                file_path
            )

            cursor = db.cursor()

            try:

                cursor.execute(
                    """
                    INSERT INTO documents (
                        user_id,
                        original_filename,
                        stored_filename,
                        file_type,
                        file_size
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        session["user_id"],
                        original_filename,
                        stored_filename,
                        extension,
                        file_size,
                    ),
                )

                db.commit()

                message = (
                    "Document uploaded successfully."
                )

                success = True

            except mysql.connector.Error:

                db.rollback()

                if os.path.exists(file_path):
                    os.remove(file_path)

                message = (
                    "The document could not be saved."
                )

            finally:

                cursor.close()

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT
            id,
            original_filename,
            file_type,
            file_size,
            uploaded_at
        FROM documents
        WHERE user_id = %s
        ORDER BY uploaded_at DESC
        """,
        (session["user_id"],),
    )

    documents_data = cursor.fetchall()

    cursor.close()

    return render_template(
        "documents.html",
        documents=documents_data,
        message=message,
        success=success,
    )
@app.route(
    "/documents/<int:document_id>/download"
)
def download_document(document_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT
            id,
            original_filename,
            stored_filename
        FROM documents
        WHERE id = %s
        AND user_id = %s
        """,
        (
            document_id,
            session["user_id"],
        ),
    )

    document = cursor.fetchone()

    cursor.close()

    if document is None:
        abort(404)

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        document["stored_filename"],
    )

    if not os.path.exists(file_path):
        abort(404)

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        document["stored_filename"],
        as_attachment=True,
        download_name=document[
            "original_filename"
        ],
    )
@app.route(
    "/documents/<int:document_id>/delete",
    methods=["POST"],
)
def delete_document(document_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT
            id,
            stored_filename
        FROM documents
        WHERE id = %s
        AND user_id = %s
        """,
        (
            document_id,
            session["user_id"],
        ),
    )

    document = cursor.fetchone()

    if document is None:

        cursor.close()

        abort(404)

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        document["stored_filename"],
    )

    try:

        if os.path.exists(file_path):
            os.remove(file_path)

        cursor.execute(
            """
            DELETE FROM documents
            WHERE id = %s
            AND user_id = %s
            """,
            (
                document_id,
                session["user_id"],
            ),
        )

        db.commit()

        flash(
            "Document deleted successfully.",
            "success",
        )

    except (
        OSError,
        mysql.connector.Error,
    ):

        db.rollback()

        flash(
            "The document could not be deleted.",
            "error",
        )

    finally:

        cursor.close()

    return redirect(
        url_for("documents")
    )
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