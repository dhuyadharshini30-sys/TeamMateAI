from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

import os
import sqlite3

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from config import Config


# ==========================================
# FLASK APP
# ==========================================

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(
    app.config["UPLOAD_FOLDER"],
    exist_ok=True
)


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db():
    conn = sqlite3.connect("teammate_ai.db")
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================
# INITIALIZE DATABASE
# ==========================================

def init_db():

    conn = get_db()

    # ======================================
    # USERS TABLE
    # ======================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            department TEXT,
            year TEXT,
            bio TEXT,
            availability TEXT DEFAULT 'Available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ======================================
    # PROJECTS TABLE
    # ======================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project_name TEXT NOT NULL,
            description TEXT NOT NULL,
            required_members INTEGER NOT NULL,
            skills TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # ======================================
    # TEAMS TABLE
    # ======================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'Member',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()


# Create database automatically
init_db()


# ==========================================
# HOME
# ==========================================

@app.route("/")
def index():

    return render_template("index.html")


# ==========================================
# REGISTER
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        department = request.form.get(
            "department",
            ""
        ).strip()

        year = request.form.get(
            "year",
            ""
        ).strip()

        bio = request.form.get(
            "bio",
            ""
        ).strip()

        # Validation
        if not name or not email or not password:

            flash(
                "Please fill all required fields.",
                "error"
            )

            return render_template(
                "register.html"
            )

        conn = None

        try:

            conn = get_db()

            # Check existing email
            existing_user = conn.execute(
                """
                SELECT id
                FROM users
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

            if existing_user:

                flash(
                    "Email already registered. Please login.",
                    "error"
                )

                return render_template(
                    "register.html"
                )

            # Hash password
            hashed_password = generate_password_hash(
                password
            )

            # Insert user
            cursor = conn.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password,
                    department,
                    year,
                    bio,
                    availability
                )
                VALUES
                (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    name,
                    email,
                    hashed_password,
                    department,
                    year,
                    bio,
                    "Available"
                )
            )

            conn.commit()

            # Get user ID
            user_id = cursor.lastrowid

            # Create session
            session["user_id"] = user_id
            session["user_name"] = name
            session["user_email"] = email

            flash(
                "Registration successful!",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        except sqlite3.Error as e:

            if conn:
                conn.rollback()

            print(
                "DATABASE ERROR:",
                e
            )

            flash(
                "Database error occurred.",
                "error"
            )

            return render_template(
                "register.html"
            )

        finally:

            if conn:
                conn.close()

    return render_template(
        "register.html"
    )


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            flash(
                "Please enter email and password.",
                "error"
            )

            return render_template(
                "login.html"
            )

        conn = None

        try:

            conn = get_db()

            # Find user
            user = conn.execute(
                """
                SELECT *
                FROM users
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

            if user and check_password_hash(
                user["password"],
                password
            ):

                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]

                flash(
                    "Login successful!",
                    "success"
                )

                return redirect(
                    url_for("dashboard")
                )

            flash(
                "Invalid email or password.",
                "error"
            )

        except sqlite3.Error as e:

            print(
                "DATABASE ERROR:",
                e
            )

            flash(
                "Database connection failed.",
                "error"
            )

        finally:

            if conn:
                conn.close()

    return render_template(
        "login.html"
    )


# ==========================================
# CREATE PROJECT
# ==========================================

@app.route(
    "/projects/create",
    methods=["GET", "POST"]
)
def create_project():

    # Login check
    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        project_name = request.form.get(
            "project_name",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        skills = request.form.get(
            "skills",
            ""
        ).strip()

        required_members_value = request.form.get(
            "required_members",
            ""
        ).strip()

        # Convert to integer
        try:

            required_members = int(
                required_members_value
            )

        except ValueError:

            required_members = 0

        # Validation
        if (
            not project_name
            or not description
            or not skills
            or required_members < 2
            or required_members > 20
        ):

            flash(
                "Please provide valid project details.",
                "error"
            )

            return render_template(
                "create_project.html"
            )

        conn = None

        try:

            conn = get_db()

            conn.execute(
                """
                INSERT INTO projects
                (
                    user_id,
                    project_name,
                    description,
                    required_members,
                    skills
                )
                VALUES
                (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    session["user_id"],
                    project_name,
                    description,
                    required_members,
                    skills
                )
            )

            conn.commit()

            flash(
                "Project created successfully.",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        except sqlite3.Error as e:

            print(
                "DATABASE ERROR:",
                e
            )

            flash(
                "Unable to create the project.",
                "error"
            )

        finally:

            if conn:
                conn.close()

    return render_template(
        "create_project.html"
    )


# ==========================================
# CREATE TEAM
# ==========================================

@app.route(
    "/projects/<int:project_id>/team",
    methods=["GET", "POST"]
)
def create_team(project_id):

    # Login check
    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = None

    try:

        conn = get_db()

        # ======================================
        # GET PROJECT
        # ======================================

        project = conn.execute(
            """
            SELECT *
            FROM projects
            WHERE id = ?
            """,
            (project_id,)
        ).fetchone()

        if not project:

            flash(
                "Project not found.",
                "error"
            )

            return redirect(
                url_for("dashboard")
            )

        # ======================================
        # CHECK PROJECT OWNER
        # ======================================

        if project["user_id"] != session["user_id"]:

            flash(
                "You are not allowed to manage this project.",
                "error"
            )

            return redirect(
                url_for("dashboard")
            )

        # ======================================
        # ADD TEAM MEMBER
        # ======================================

        if request.method == "POST":

            member_id_value = request.form.get(
                "member_id",
                ""
            ).strip()

            role = request.form.get(
                "role",
                "Member"
            ).strip()

            # Convert ID
            try:

                member_id = int(
                    member_id_value
                )

            except ValueError:

                member_id = 0

            if member_id <= 0:

                flash(
                    "Please select a valid member.",
                    "error"
                )

                return redirect(
                    url_for(
                        "create_team",
                        project_id=project_id
                    )
                )

            # ==================================
            # CHECK USER
            # ==================================

            member = conn.execute(
                """
                SELECT *
                FROM users
                WHERE id = ?
                """,
                (member_id,)
            ).fetchone()

            if not member:

                flash(
                    "Selected member does not exist.",
                    "error"
                )

                return redirect(
                    url_for(
                        "create_team",
                        project_id=project_id
                    )
                )

            # ==================================
            # CHECK DUPLICATE
            # ==================================

            existing_member = conn.execute(
                """
                SELECT id
                FROM teams
                WHERE project_id = ?
                AND user_id = ?
                """,
                (
                    project_id,
                    member_id
                )
            ).fetchone()

            if existing_member:

                flash(
                    "This student is already in the team.",
                    "error"
                )

                return redirect(
                    url_for(
                        "create_team",
                        project_id=project_id
                    )
                )

            # ==================================
            # CHECK TEAM LIMIT
            # ==================================

            team_count = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM teams
                WHERE project_id = ?
                """,
                (project_id,)
            ).fetchone()

            current_count = team_count["count"]

            if current_count >= project["required_members"]:

                flash(
                    "The team has already reached the required member limit.",
                    "error"
                )

                return redirect(
                    url_for(
                        "create_team",
                        project_id=project_id
                    )
                )

            # ==================================
            # ADD MEMBER
            # ==================================

            conn.execute(
                """
                INSERT INTO teams
                (
                    project_id,
                    user_id,
                    role
                )
                VALUES
                (
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    project_id,
                    member_id,
                    role or "Member"
                )
            )

            conn.commit()

            flash(
                "Team member added successfully!",
                "success"
            )

            return redirect(
                url_for(
                    "create_team",
                    project_id=project_id
                )
            )

        # ======================================
        # GET CURRENT TEAM MEMBERS
        # ======================================

        team_members = conn.execute(
            """
            SELECT
                t.id AS team_id,
                t.role,
                t.joined_at,
                u.id AS user_id,
                u.name,
                u.email,
                u.department,
                u.year,
                u.bio,
                u.availability
            FROM teams AS t
            JOIN users AS u
                ON t.user_id = u.id
            WHERE t.project_id = ?
            ORDER BY t.joined_at ASC
            """,
            (project_id,)
        ).fetchall()

        # ======================================
        # GET AVAILABLE USERS
        # ======================================

        available_users = conn.execute(
            """
            SELECT *
            FROM users
            WHERE id != ?
            AND id NOT IN
            (
                SELECT user_id
                FROM teams
                WHERE project_id = ?
            )
            ORDER BY name ASC
            """,
            (
                session["user_id"],
                project_id
            )
        ).fetchall()

        return render_template(
            "create_team.html",
            project=project,
            team_members=team_members,
            available_users=available_users,
            team_count=len(team_members)
        )

    except sqlite3.Error as e:

        if conn:
            conn.rollback()

        print(
            "DATABASE ERROR:",
            e
        )

        flash(
            "Unable to load team information.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    finally:

        if conn:
            conn.close()


# ==========================================
# REMOVE TEAM MEMBER
# ==========================================

@app.route(
    "/projects/<int:project_id>/team/remove/<int:member_id>",
    methods=["POST"]
)
def remove_team_member(
    project_id,
    member_id
):

    # Login check
    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = None

    try:

        conn = get_db()

        # Check project ownership
        project = conn.execute(
            """
            SELECT *
            FROM projects
            WHERE id = ?
            AND user_id = ?
            """,
            (
                project_id,
                session["user_id"]
            )
        ).fetchone()

        if not project:

            flash(
                "Project not found or access denied.",
                "error"
            )

            return redirect(
                url_for("dashboard")
            )

        # Delete member
        conn.execute(
            """
            DELETE FROM teams
            WHERE project_id = ?
            AND user_id = ?
            """,
            (
                project_id,
                member_id
            )
        )

        conn.commit()

        flash(
            "Team member removed.",
            "success"
        )

        return redirect(
            url_for(
                "create_team",
                project_id=project_id
            )
        )

    except sqlite3.Error as e:

        if conn:
            conn.rollback()

        print(
            "DATABASE ERROR:",
            e
        )

        flash(
            "Unable to remove team member.",
            "error"
        )

        return redirect(
            url_for(
                "create_team",
                project_id=project_id
            )
        )

    finally:

        if conn:
            conn.close()


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = None

    try:

        conn = get_db()

        # ======================================
        # GET USER
        # ======================================

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (session["user_id"],)
        ).fetchone()

        if not user:

            session.clear()

            return redirect(
                url_for("login")
            )

        # ======================================
        # GET PROJECTS
        # ======================================

        projects = conn.execute(
            """
            SELECT
                p.*,
                (
                    SELECT COUNT(*)
                    FROM teams AS t
                    WHERE t.project_id = p.id
                ) AS member_count
            FROM projects AS p
            WHERE p.user_id = ?
            ORDER BY
                p.created_at DESC,
                p.id DESC
            """,
            (session["user_id"],)
        ).fetchall()

        return render_template(
            "dashboard.html",
            user=user,
            projects=projects
        )

    except sqlite3.Error as e:

        print(
            "DATABASE ERROR:",
            e
        )

        return f"""
        <h2>Database Error</h2>
        <p>{e}</p>
        """

    finally:

        if conn:
            conn.close()


# ==========================================
# PROFILE
# ==========================================

@app.route("/profile")
def profile():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = None

    try:

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (session["user_id"],)
        ).fetchone()

        if not user:

            session.clear()

            return redirect(
                url_for("login")
            )

        return render_template(
            "profile.html",
            user=user
        )

    except sqlite3.Error as e:

        print(
            "DATABASE ERROR:",
            e
        )

        return f"""
        <h2>Database Error</h2>
        <p>{e}</p>
        """

    finally:

        if conn:
            conn.close()


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("index")
    )


# ==========================================
# DATABASE TEST
# ==========================================

@app.route("/db-test")
def db_test():

    conn = None

    try:

        conn = get_db()

        result = conn.execute(
            "SELECT sqlite_version()"
        ).fetchone()

        return f"""
        <h1>Database Connected Successfully ✅</h1>
        <p>Database: SQLite</p>
        <p>SQLite Version: {result[0]}</p>
        """

    except sqlite3.Error as e:

        return f"""
        <h1>Database Connection Failed ❌</h1>
        <p>{e}</p>
        """

    finally:

        if conn:
            conn.close()


# ==========================================
# TEST
# ==========================================

@app.route("/test")
def test():

    return "TeamMate AI Backend is Working! 🚀"


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    print("================================")
    print("       TEAMMATE AI STARTED")
    print("================================")
    print("Database: SQLite")
    print("Open: http://127.0.0.1:5000")

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )