import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER, MAX_CONTENT_LENGTH, SECRET_KEY
from models import (
    create_meal_doc, update_meal_labels_and_nutrients, get_meal,
    create_nutrition_plan, plans_col, get_total_intake_for_day,
    get_active_plan_for_mother_and_date, users_col, create_alert,
    get_active_alerts, meals_col
)
from utils.ocr_dummy import analyze_image_dummy
from bson.objectid import ObjectId
from datetime import datetime
import json
import random
from werkzeug.security import generate_password_hash, check_password_hash

# IMPORTANT for ASHA worker feature
from models import db

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
    "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands",
    "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]

INCOME_RANGES = [
    "< ₹1,00,000",
    "₹1,00,000 – ₹3,00,000",
    "₹3,00,000 – ₹6,00,000",
    ">₹6,00,000"
]

DIETARY_PREFERENCES = ["Vegetarian", "Non-Vegetarian", "Eggitarian"]

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["SECRET_KEY"] = SECRET_KEY


# -------------------------------------------------
# Helper: Assign random ASHA worker to a mother
# -------------------------------------------------
def assign_random_asha():
    asha_workers = list(users_col.find({"role": "asha"}))
    if not asha_workers:
        return None
    selected = random.choice(asha_workers)
    return str(selected["_id"])


# -------------------------------------------------
# INDEX
# -------------------------------------------------
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    role = session.get("role")

    if role == "mother":
        return redirect(url_for("mother_page"))
    elif role == "doctor":
        return redirect(url_for("doctor_page"))
    elif role == "asha":
        return redirect(url_for("asha_page"))

    return redirect(url_for("login"))


# -------------------------------------------------
# LOGIN
# -------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        user = users_col.find_one({"email": email, "role": role})
        if not user:
            return render_template("login.html", error="User not found with selected role.")

        if not check_password_hash(user["password"], password):
            return render_template("login.html", error="Invalid password.")

        session["user_id"] = str(user["_id"])
        session["role"] = user["role"]

        return redirect(url_for("index"))

    return render_template("login.html")


# -------------------------------------------------
# SIGNUP
# -------------------------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        role = request.form.get("role")
        email = request.form.get("email")
        password = request.form.get("password")

        if not role or not email or not password:
            return render_template("signup.html", error="Missing fields",
                                   states=INDIAN_STATES, incomes=INCOME_RANGES, diets=DIETARY_PREFERENCES)

        if users_col.find_one({"email": email}):
            return render_template("signup.html", error="Email already exists",
                                   states=INDIAN_STATES, incomes=INCOME_RANGES, diets=DIETARY_PREFERENCES)

        hashed_password = generate_password_hash(password)

        user_doc = {
            "email": email,
            "password": hashed_password,
            "role": role,
            "createdAt": datetime.utcnow()
        }

        # -----------------------
        # MOTHER SIGNUP
        # -----------------------
        if role == "mother":
            assigned_asha = assign_random_asha()

            user_doc.update({
                "name": request.form.get("name"),
                "age": request.form.get("age"),
                "gender": request.form.get("gender"),
                "location_state": request.form.get("state"),
                "location_area_type": request.form.get("area_type"),
                "income_range": request.form.get("income"),
                "dietary_preference": request.form.get("diet"),
                "ashaId": assigned_asha
            })

        # Doctor signup
        elif role == "doctor":
            user_doc.update({
                "name": request.form.get("name")
            })

        # ASHA signup
        elif role == "asha":
            user_doc.update({
                "name": request.form.get("name"),
                "asha_worker_id": request.form.get("asha_worker_id"),
                "phone": request.form.get("phone"),
                "assigned_area": request.form.get("assigned_area")
            })

        # Insert user
        result = users_col.insert_one(user_doc)
        new_user_id = str(result.inserted_id)

        # Store assignment in DB
        if role == "mother" and user_doc.get("ashaId"):
            db.asha_assignments.insert_one({
                "ashaId": user_doc["ashaId"],
                "motherId": new_user_id,
                "active": True,
                "createdAt": datetime.utcnow()
            })

        # SESSION LOGIN
        session["user_id"] = new_user_id
        session["role"] = role

        if role == "mother":
            return redirect(url_for("mother_page"))
        elif role == "doctor":
            return redirect(url_for("doctor_page"))
        elif role == "asha":
            return redirect(url_for("asha_page"))

    return render_template("signup.html",
                           states=INDIAN_STATES, incomes=INCOME_RANGES, diets=DIETARY_PREFERENCES)


# -------------------------------------------------
# LOGOUT
# -------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -------------------------------------------------
# MOTHER PAGE
# -------------------------------------------------
@app.route("/mother")
def mother_page():
    if session.get("role") != "mother":
        return redirect(url_for("login"))
    return render_template("mother.html", mother_id=session["user_id"])


# -------------------------------------------------
# DOCTOR PAGE
# -------------------------------------------------
@app.route("/doctor")
def doctor_page():
    if session.get("role") != "doctor":
        return redirect(url_for("login"))
    return render_template("doctor.html", doctor_id=session["user_id"])


# -------------------------------------------------
# ASHA PAGE
# -------------------------------------------------
@app.route("/asha")
def asha_page():
    if session.get("role") != "asha":
        return redirect(url_for("login"))
    return render_template("asha.html", asha_id=session["user_id"])


# -------------------------------------------------
# API ROUTES (UNCHANGED — YOUR ORIGINAL CODE)
# -------------------------------------------------

@app.route("/api/meals/upload", methods=["POST"])
def upload_meal():
    mother_id = session.get("user_id") or request.form.get("motherId")
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
    dish_name = ocr_result["nutrients"]["dish_name"]
    nutrients = {k: v for k, v in ocr_result["nutrients"].items() if k != "dish_name"}

    updated = update_meal_labels_and_nutrients(meal_id, ocr_result.get("labels"), nutrients, dish_name)

    updated['_id'] = str(updated['_id'])

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


@app.route("/api/meals/<meal_id>", methods=["GET"])
def get_meal_api(meal_id):
    try:
        meal = get_meal(meal_id)
    except Exception:
        return jsonify({"error": "invalid id"}), 400

    if not meal:
        return jsonify({"error": "not found"}), 404

    meal['_id'] = str(meal['_id'])
    return jsonify(meal)


@app.route("/api/nutrition-plans", methods=["POST"])
def create_plan_api():
    data = request.get_json() or {}
    mother_id = data.get("motherId")
    title = data.get("title", "Daily Nutrition Plan")
    required_nutrients = data.get("required_nutrients", {})

    if not mother_id or not required_nutrients:
        return jsonify({"error": "motherId and required_nutrients are required"}), 400

    plan_doc = {
        "motherId": mother_id,
        "title": title,
        "required_nutrients": required_nutrients,
        "status": "active",
        "createdAt": datetime.utcnow()
    }

    res = plans_col.insert_one(plan_doc)
    plan_doc["_id"] = str(res.inserted_id)
    return jsonify({"plan": plan_doc}), 201


@app.route("/api/meals/mother/<mother_id>", methods=["GET"])
def get_meals_for_mother(mother_id):
    meals = list(meals_col.find({"motherId": mother_id}).sort("mealDate", -1))
    for m in meals:
        m["_id"] = str(m["_id"])
    return jsonify(meals)


@app.route("/api/alerts/<mother_id>", methods=["GET"])
def get_alerts_for_mother(mother_id):
    alerts = get_active_alerts(mother_id)
    return jsonify(alerts)


@app.route("/api/nutrients/remaining/<mother_id>", methods=["GET"])
def get_remaining_nutrients(mother_id):
    today = datetime.now().strftime("%Y-%m-%d")

    plan = get_active_plan_for_mother_and_date(mother_id, today)
    if not plan or not plan.get("required_nutrients"):
        return jsonify({"error": "No active plan found for today"}), 404

    daily_goal = {}
    for meal_type_data in plan["required_nutrients"].values():
        for k, v in meal_type_data.items():
            daily_goal[k] = daily_goal.get(k, 0) + v

    total_intake = get_total_intake_for_day(mother_id, today)

    remaining = {}
    for k, goal in daily_goal.items():
        taken = total_intake.get(k, 0)
        remaining[k] = round(max(goal - taken, 0), 2)

    return jsonify({
        "date": today,
        "required": daily_goal,
        "consumed": total_intake,
        "remaining": remaining
    })


# -------------------------------------------------
# ASHA WORKER ROUTES
# -------------------------------------------------



@app.route("/api/asha/assignments", methods=["GET"])
def api_asha_assignments():
    asha_id = session.get("user_id") or request.args.get("ashaId")
    assigns = list(db.asha_assignments.find({"ashaId": asha_id, "active": True}))
    for a in assigns:
        a["_id"] = str(a["_id"])
    return jsonify(assigns)


@app.route("/api/asha/mothers/<asha_id>", methods=["GET"])
def api_get_mothers_for_asha(asha_id):
    from models import get_mothers_for_asha
    mothers = get_mothers_for_asha(asha_id)
    return jsonify(mothers)


@app.route("/api/asha/visits", methods=["POST"])
def api_create_visit():
    data = request.form.to_dict() or request.get_json() or {}
    asha_id = session.get("user_id") or data.get("ashaId")
    mother_id = data.get("motherId")
    visit_date = data.get("visitDate")
    visit_type = data.get("type", "spot-check")
    observations = data.get("observations")

    photos = []
    if "photo" in request.files:
        f = request.files["photo"]
        filename = secure_filename(f.filename)
        p = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        f.save(p)
        photos.append(p)

    from models import create_visit_record
    rec = create_visit_record(
        asha_id, mother_id, visit_date, visit_type,
        observations=observations, photos=photos
    )
    return jsonify(rec), 201


@app.route("/api/asha/alerts", methods=["GET"])
def api_asha_alerts():
    asha_id = session.get("user_id") or request.args.get("ashaId")
    from models import get_active_alerts_for_asha
    alerts = get_active_alerts_for_asha(asha_id)
    return jsonify(alerts)


@app.route("/api/asha/alerts/<alert_id>/triage", methods=["POST"])
def api_triage_alert(alert_id):
    data = request.get_json() or {}
    asha_id = session.get("user_id") or data.get("ashaId")
    action = data.get("action")
    notes = data.get("notes")
    escalate = data.get("escalate", False)

    from models import triage_alert
    updated = triage_alert(alert_id, asha_id, action, notes, escalate_to_doctor=escalate)
    return jsonify(updated)

from datetime import timedelta

@app.route("/api/asha/mother_details/<mother_id>", methods=["GET"])
def api_asha_mother_details(mother_id):
    from models import get_active_plan_for_mother_and_date

    mother = users_col.find_one({"_id": ObjectId(mother_id)})
    if not mother:
        return jsonify({"error": "Mother not found"}), 404

    mother["_id"] = str(mother["_id"])

    details = {
        "profile": {
            "name": mother.get("name"),
            "age": mother.get("age"),
            "gender": mother.get("gender"),
            "state": mother.get("location_state"),
            "area_type": mother.get("location_area_type"),
            "income": mother.get("income_range"),
            "diet": mother.get("dietary_preference"),
        }
    }

    # Today's plan
    today = datetime.now().strftime("%Y-%m-%d")
    plan = get_active_plan_for_mother_and_date(mother_id, today)
    if plan:
        plan["_id"] = str(plan["_id"])
    details["plan"] = plan or {}

    # Weekly meal history
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    meals = list(meals_col.find({
        "motherId": mother_id,
        "mealDate": {"$gte": week_ago}
    }))
    for m in meals:
        m["_id"] = str(m["_id"])
    details["weekly_meals"] = meals

    # Alerts
    alerts = list(db.alerts.find({
        "motherId": mother_id,
        "status": "active"
    }))
    for a in alerts:
        a["_id"] = str(a["_id"])
    details["alerts"] = alerts

    return jsonify(details)


# -------------------------------------------------
# MAIN
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
