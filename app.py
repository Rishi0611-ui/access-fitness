"""ACEest Fitness & Gym - Flask web app.

The logic here is ported from the Tkinter desktop versions (v1.0 -> v3.2.4):
  v1.0 / v1.1   : programs (workout + diet) and calorie estimation
  v1.1.2        : CSV export
  v2.x          : SQLite clients and weekly progress (adherence)
  v2.2.x        : BMI and risk info
  v3.x          : membership status, workout logging, program generator
"""
import csv
import io
import os
import random
import sqlite3
from datetime import date, datetime

from flask import Flask, Response, g, jsonify, request

# ---------- STATIC DATA (from v1.1 / v2.2.4 / v3.2.4) ----------
PROGRAMS = {
    "FL": {
        "name": "Fat Loss (FL)",
        "workout": [
            "Mon: Back Squat 5x5 + Core",
            "Tue: EMOM 20min Assault Bike",
            "Wed: Bench Press + 21-15-9",
            "Thu: Deadlift + Box Jumps",
            "Fri: Zone 2 Cardio 30min",
        ],
        "diet": [
            "Breakfast: Egg Whites + Oats",
            "Lunch: Grilled Chicken + Brown Rice",
            "Dinner: Fish Curry + Millet Roti",
            "Target: ~2000 kcal",
        ],
        "calorie_factor": 22,
    },
    "MG": {
        "name": "Muscle Gain (MG)",
        "workout": [
            "Mon: Squat 5x5",
            "Tue: Bench 5x5",
            "Wed: Deadlift 4x6",
            "Thu: Front Squat 4x8",
            "Fri: Incline Press 4x10",
            "Sat: Barbell Rows 4x10",
        ],
        "diet": [
            "Breakfast: Eggs + Peanut Butter Oats",
            "Lunch: Chicken Biryani",
            "Dinner: Mutton Curry + Rice",
            "Target: ~3200 kcal",
        ],
        "calorie_factor": 35,
    },
    "BG": {
        "name": "Beginner (BG)",
        "workout": [
            "Full Body Circuit: Air Squats, Ring Rows, Push-ups",
            "Focus: Technique & Consistency",
        ],
        "diet": [
            "Balanced Tamil Meals: Idli / Dosa / Rice + Dal",
            "Protein Target: 120g/day",
        ],
        "calorie_factor": 26,
    },
}

PROGRAM_TEMPLATES = {
    "FL": ["Full Body HIIT", "Circuit Training", "Cardio + Weights"],
    "MG": ["Push/Pull/Legs", "Upper/Lower Split", "Full Body Strength"],
    "BG": ["Full Body 3x/week", "Light Strength + Mobility"],
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    age INTEGER,
    height REAL,
    weight REAL,
    program TEXT,
    calories INTEGER,
    membership_status TEXT DEFAULT 'Active',
    membership_end TEXT
);
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    week TEXT NOT NULL,
    adherence INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    date TEXT NOT NULL,
    workout_type TEXT NOT NULL,
    duration_min INTEGER,
    notes TEXT
);
"""


# ---------- PURE HELPERS (easy to unit test) ----------
def estimate_calories(weight, program_code):
    """Calories = weight(kg) * program calorie factor (v1.1 logic)."""
    if program_code not in PROGRAMS or not weight or weight <= 0:
        return None
    return int(weight * PROGRAMS[program_code]["calorie_factor"])


def calculate_bmi(height_cm, weight_kg):
    """Return (bmi, category, risk) using the v2.2.4 rules."""
    if height_cm <= 0 or weight_kg <= 0:
        raise ValueError("height and weight must be positive")
    h_m = height_cm / 100.0
    bmi = round(weight_kg / (h_m * h_m), 1)
    if bmi < 18.5:
        return bmi, "Underweight", "Potential nutrient deficiency, low energy."
    if bmi < 25:
        return bmi, "Normal", "Low risk if active and strong."
    if bmi < 30:
        return bmi, "Overweight", "Moderate risk; focus on adherence and progressive activity."
    return bmi, "Obese", "Higher risk; prioritize fat loss, consistency, and supervision."


def membership_state(status, end_date):
    """Return 'Active' or 'Expired' based on status and end date (v3.x)."""
    if status and status.lower() != "active":
        return status
    if end_date:
        try:
            if datetime.strptime(end_date, "%Y-%m-%d").date() < date.today():
                return "Expired"
        except ValueError:
            return "Unknown"
    return "Active"


# ---------- APP FACTORY ----------
def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("ACEEST_DB", "aceest_fitness.db")

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with sqlite3.connect(app.config["DB_PATH"]) as conn:
        conn.executescript(SCHEMA)

    def error(message, code=400):
        return jsonify({"error": message}), code

    def find_client(name):
        return get_db().execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()

    # ----- general -----
    @app.get("/")
    def index():
        return jsonify({"app": "ACEest Fitness & Gym", "status": "ok"})

    @app.get("/health")
    def health():
        return jsonify({"status": "healthy"})

    # ----- programs (v1.0 / v1.1) -----
    @app.get("/programs")
    def list_programs():
        return jsonify({code: p["name"] for code, p in PROGRAMS.items()})

    @app.get("/programs/<code>")
    def get_program(code):
        program = PROGRAMS.get(code.upper())
        if not program:
            return error("program not found", 404)
        return jsonify(program)

    @app.get("/generate-program/<code>")
    def generate_program(code):
        templates = PROGRAM_TEMPLATES.get(code.upper())
        if not templates:
            return error("program not found", 404)
        return jsonify({"program": code.upper(), "suggestion": random.choice(templates)})

    # ----- clients (v2.x) -----
    @app.post("/clients")
    def add_client():
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        if not name:
            return error("name is required")
        program = str(data.get("program", "")).upper() or None
        if program and program not in PROGRAMS:
            return error("invalid program")
        try:
            age = int(data["age"]) if data.get("age") is not None else None
            height = float(data["height"]) if data.get("height") is not None else None
            weight = float(data["weight"]) if data.get("weight") is not None else None
        except (TypeError, ValueError):
            return error("age, height and weight must be numbers")
        if find_client(name):
            return error("client already exists", 409)
        calories = estimate_calories(weight, program)
        db = get_db()
        db.execute(
            "INSERT INTO clients (name, age, height, weight, program, calories,"
            " membership_status, membership_end) VALUES (?,?,?,?,?,?,?,?)",
            (name, age, height, weight, program, calories,
             data.get("membership_status", "Active"), data.get("membership_end")),
        )
        db.commit()
        return jsonify(dict(find_client(name))), 201

    @app.get("/clients")
    def list_clients():
        rows = get_db().execute("SELECT * FROM clients ORDER BY name").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/clients/<name>")
    def get_client(name):
        client = find_client(name)
        if not client:
            return error("client not found", 404)
        return jsonify(dict(client))

    @app.delete("/clients/<name>")
    def delete_client(name):
        if not find_client(name):
            return error("client not found", 404)
        db = get_db()
        for table, col in (("progress", "client_name"), ("workouts", "client_name"),
                           ("clients", "name")):
            db.execute(f"DELETE FROM {table} WHERE {col}=?", (name,))
        db.commit()
        return jsonify({"deleted": name})

    # ----- progress (v2.x) -----
    @app.post("/clients/<name>/progress")
    def add_progress(name):
        if not find_client(name):
            return error("client not found", 404)
        data = request.get_json(silent=True) or {}
        week = str(data.get("week", "")).strip()
        try:
            adherence = int(data.get("adherence"))
        except (TypeError, ValueError):
            return error("adherence must be a number")
        if not week or not 0 <= adherence <= 100:
            return error("week is required and adherence must be 0-100")
        db = get_db()
        db.execute("INSERT INTO progress (client_name, week, adherence) VALUES (?,?,?)",
                   (name, week, adherence))
        db.commit()
        return jsonify({"client": name, "week": week, "adherence": adherence}), 201

    @app.get("/clients/<name>/summary")
    def summary(name):
        client = find_client(name)
        if not client:
            return error("client not found", 404)
        row = get_db().execute(
            "SELECT COUNT(*) AS weeks, AVG(adherence) AS avg FROM progress WHERE client_name=?",
            (name,)).fetchone()
        avg = round(row["avg"], 1) if row["avg"] is not None else 0
        return jsonify({"client": name, "program": client["program"],
                        "calories": client["calories"], "weeks_logged": row["weeks"],
                        "average_adherence": avg})

    # ----- BMI (v2.2.x) -----
    @app.get("/clients/<name>/bmi")
    def bmi(name):
        client = find_client(name)
        if not client:
            return error("client not found", 404)
        try:
            value, category, risk = calculate_bmi(client["height"] or 0, client["weight"] or 0)
        except ValueError:
            return error("valid height and weight are required")
        return jsonify({"client": name, "bmi": value, "category": category, "risk": risk})

    # ----- workouts (v3.x) -----
    @app.post("/clients/<name>/workouts")
    def add_workout(name):
        if not find_client(name):
            return error("client not found", 404)
        data = request.get_json(silent=True) or {}
        workout_type = str(data.get("workout_type", "")).strip()
        if not workout_type:
            return error("workout_type is required")
        workout_date = data.get("date") or date.today().isoformat()
        db = get_db()
        db.execute("INSERT INTO workouts (client_name, date, workout_type, duration_min, notes)"
                   " VALUES (?,?,?,?,?)",
                   (name, workout_date, workout_type, data.get("duration_min"),
                    data.get("notes", "")))
        db.commit()
        return jsonify({"client": name, "date": workout_date,
                        "workout_type": workout_type}), 201

    @app.get("/clients/<name>/workouts")
    def list_workouts(name):
        if not find_client(name):
            return error("client not found", 404)
        rows = get_db().execute(
            "SELECT date, workout_type, duration_min, notes FROM workouts"
            " WHERE client_name=? ORDER BY date", (name,)).fetchall()
        return jsonify([dict(r) for r in rows])

    # ----- membership (v3.x) -----
    @app.get("/clients/<name>/membership")
    def membership(name):
        client = find_client(name)
        if not client:
            return error("client not found", 404)
        state = membership_state(client["membership_status"], client["membership_end"])
        return jsonify({"client": name, "membership": state,
                        "membership_end": client["membership_end"]})

    # ----- CSV export (v1.1.2) -----
    @app.get("/export/clients.csv")
    def export_csv():
        rows = get_db().execute(
            "SELECT name, age, height, weight, program, calories FROM clients ORDER BY name"
        ).fetchall()
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["name", "age", "height", "weight", "program", "calories"])
        for r in rows:
            writer.writerow(list(r))
        return Response(out.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=clients.csv"})

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
