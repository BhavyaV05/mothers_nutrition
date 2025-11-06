import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from config import UPLOAD_FOLDER, MAX_CONTENT_LENGTH, SECRET_KEY
from models import (
    create_meal_doc, update_meal_labels_and_nutrients, get_meal, create_nutrition_plan,
    plans_col, get_total_intake_for_day, get_active_plan_for_mother_and_date,
    users_col
)
from utils.ocr_dummy import analyze_image_dummy
from bson.objectid import ObjectId
from datetime import datetime

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['SECRET_KEY'] = SECRET_KEY

# ---------------- BASIC PAGES ----------------

@app.route("/")
def index():
    if session.get("role") == "doctor":
        return redirect(url_for("doctor_page"))
    elif session.get("role") == "mother":
        return redirect(url_for("mother_page"))
    return redirect(url_for("login"))

@app.route("/mother")
def mother_page():
    return render_template("mother.html")

@app.route("/doctor")
def doctor_page():
    return render_template("doctor.html")

# ---------------- AUTH ROUTES ----------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email").lower()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        role = request.form.get("role")

        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for("signup"))

        existing = users_col.find_one({"email": email})
        if existing:
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for("login"))

        hashed_pw = generate_password_hash(password)
        users_col.insert_one({
            "full_name": full_name,
            "email": email,
            "password": hashed_pw,
            "role": role,
            "createdAt": datetime.utcnow()
        })

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email").lower()
        password = request.form.get("password")

        user = users_col.find_one({"email": email})
        if not user or not check_password_hash(user["password"], password):
            flash("Invalid email or password", "danger")
            return redirect(url_for("login"))

        session["user_id"] = str(user["_id"])
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]

        flash("Login successful!", "success")

        if user["role"] == "mother":
            return redirect(url_for("mother_page"))
        else:
            return redirect(url_for("doctor_page"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

# ---------------- API ROUTES ----------------

@app.route("/api/meals/upload", methods=["POST"])
def upload_meal():
    mother_id = request.form.get("motherId")
    meal_type = request.form.get("mealType", "unknown").lower()
    meal_date = request.form.get("mealDate")
    img = request.files.get("image")

    if not mother_id or not img:
        return jsonify({"error": "motherId and image are required"}), 400

    filename = secure_filename(img.filename)
    if filename == "":
        return jsonify({"error": "invalid filename"}), 400

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img.save(save_path)

    meal_id, _ = create_meal_doc(mother_id, meal_type, meal_date, save_path)

    ocr_result = analyze_image_dummy(save_path)
    nutrients = ocr_result.get("nutrients", {})

    updated = update_meal_labels_and_nutrients(meal_id, ocr_result.get("labels"), nutrients)
    updated['_id'] = str(updated['_id'])

    from models import create_alert
    from utils.nutrition_check import compare_nutrients

    plan = get_active_plan_for_mother_and_date(mother_id, meal_date)
    alert_info = None

    if plan and plan.get("required_nutrients") and meal_type in plan["required_nutrients"]:
        req_nutrients = plan["required_nutrients"][meal_type]
        deficits = compare_nutrients(nutrients, req_nutrients)
        if deficits:
            alert_doc = create_alert(
                mother_id=mother_id,
                meal_date=meal_date,
                nutrient_deficit=deficits
            )
            alert_info = {"alert_created": True, "deficits": deficits, "alert_id": alert_doc["_id"]}
        else:
            alert_info = {"alert_created": False}
    else:
        alert_info = {"alert_created": False, "reason": "no plan for meal type"}

    total_intake = get_total_intake_for_day(mother_id, meal_date)

    # Daily goal
    if plan and plan.get("required_nutrients"):
        daily_goal = {}
        for meal_type_data in plan["required_nutrients"].values():
            for k, v in meal_type_data.items():
                daily_goal[k] = daily_goal.get(k, 0) + v
    else:
        daily_goal = {}

    remaining = {}
    for k, goal in daily_goal.items():
        taken = total_intake.get(k, 0)
        remaining[k] = round(max(goal - taken, 0), 2)

    return jsonify({
        "meal": updated,
        "ocr_result": ocr_result,
        "meal_check": alert_info,
        "daily_summary": {
            "goal": daily_goal,
            "taken_so_far": total_intake,
            "remaining": remaining
        }
    }), 201


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
