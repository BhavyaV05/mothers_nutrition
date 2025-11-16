import os
from flask import Flask, request, jsonify, render_template, redirect, url_for,session,flash
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER, MAX_CONTENT_LENGTH, SECRET_KEY
from models import create_meal_doc, update_meal_labels_and_nutrients, get_meal, create_nutrition_plan, plans_col, get_total_intake_for_day, get_active_plan_for_mother_and_date, users_col, create_alert, get_active_alerts, meals_col,get_random_doctor_id,get_assigned_mothers,upsert_nutrition_plan,get_user_by_id
from utils.ocr_dummy import analyze_image_dummy
from bson.objectid import ObjectId
from datetime import datetime
import json
from presets import RDA_PRESETS
from werkzeug.security import generate_password_hash, check_password_hash # Add this line
# from routes.auth import auth_bp
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
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['SECRET_KEY'] = SECRET_KEY

# Simple pages
@app.route("/")
def index():
    # Redirect to login if user is not in session
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Redirect based on role
    if session.get('role') == 'mother':
        return redirect(url_for('mother_page'))
    elif session.get('role') == 'doctor':
        return redirect(url_for('doctor_page'))
    return redirect(url_for('login')) # Fallback
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")
        
        # 1. Check user in database
        user = users_col.find_one({"email": email, "role": role})

        # 2. Basic Auth Check (Replace with secure password hashing/verification)
        if user and check_password_hash(user.get("password"), password):
            session['user_id'] = str(user['_id'])
            session['role'] = user['role']
            
            if user['role'] == 'mother':
                return redirect(url_for('mother_page'))
            elif user['role'] == 'doctor':
                return redirect(url_for('doctor_page'))
        
        # Authentication failed
        error = "Invalid credentials or role."
        return render_template("login.html", error=error)
        
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        role = request.form.get("role")
        email = request.form.get("email")
        password = request.form.get("password")
        if not role or not email or not password:
             error = "Role, email, and password are required."
             return render_template("signup.html", error=error, states=INDIAN_STATES, incomes=INCOME_RANGES, diets=DIETARY_PREFERENCES)
        # Check if user already exists
        if users_col.find_one({"email": email}):
            error = "An account with this email already exists."
            return render_template("signup.html", error=error, states=INDIAN_STATES, incomes=INCOME_RANGES, diets=DIETARY_PREFERENCES)
        hashed_password = generate_password_hash(password)

        user_doc = {
            "email": email,
            "password": hashed_password, # Hash this securely!
            "role": role,
            "createdAt": datetime.utcnow()
        }

        if role == 'mother':
            # Mother-specific fields
            assigned_doctor_id = get_random_doctor_id()
            if not assigned_doctor_id:
                error = "Cannot register mother: No doctors available for assignment."
                return render_template("signup.html", error=error, states=INDIAN_STATES, incomes=INCOME_RANGES, diets=DIETARY_PREFERENCES)
            user_doc.update({
                "assigned_doctor_id": assigned_doctor_id,
                "name": request.form.get("name"),
                "age": request.form.get("age"),
                "gender": request.form.get("gender"), # Though usually female for 'mother', it's good practice
                "location_state": request.form.get("state"),
                "location_area_type": request.form.get("area_type"),
                "income_range": request.form.get("income"),
                "dietary_preference": request.form.get("diet")
            })
            
        elif role == 'doctor':
            # Doctor-specific fields (add as needed)
            user_doc.update({
                "name": request.form.get("name")
            })

        try:
            result = users_col.insert_one(user_doc)
            session['user_id'] = str(result.inserted_id)
            session['role'] = role
            return redirect(url_for('index'))
        except Exception as e:
            print(f"Signup error: {e}")
            error = "Could not create user. Please try again."
            return render_template("signup.html", error=error, states=INDIAN_STATES, incomes=INCOME_RANGES, diets=DIETARY_PREFERENCES)


    return render_template("signup.html", states=INDIAN_STATES, incomes=INCOME_RANGES, diets=DIETARY_PREFERENCES)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('login'))

@app.route("/mother")
def mother_page():
    if session.get('role') != 'mother':
        return redirect(url_for('login'))
    mother_id = session['user_id']
    mother_data = users_col.find_one({"_id": ObjectId(mother_id)})
    assigned_doctor_id = mother_data.get("assigned_doctor_id") if mother_data else None
    return render_template("mother.html", 
                           mother_id=mother_id, 
                           assigned_doctor_id=assigned_doctor_id)

@app.route("/doctor")
def doctor_page():
    if session.get('role') != 'doctor':
        return redirect(url_for('login'))
    
    # This page will now list the doctor's assigned mothers
    doctor_id = session['user_id']
    mothers = get_assigned_mothers(doctor_id)
    
    return render_template("doctor.html", 
                           doctor_id=doctor_id, 
                           mothers=mothers) # Pass mothers to the template
# In app.py
@app.route("/doctor/patient/<string:mother_id>", methods=["GET", "POST"])
def doctor_patient_profile(mother_id):
    # Security check: Ensure doctor is logged in and assigned this mother
    if session.get('role') != 'doctor':
        return redirect(url_for('login'))
        
    mother = get_user_by_id(mother_id)
    if not mother or mother.get("assigned_doctor_id") != session.get("user_id"):
        flash("Unauthorized: You are not assigned to this patient.", "error")
        return redirect(url_for('doctor_page'))

    if request.method == "POST":
        # === Form is being submitted, save the data ===
        
        # 1. Build the required_nutrients dictionary from the form
        #    This is now updated with all the new fields
        required_nutrients = {
            "breakfast": {
                "kcal": request.form.get('breakfast-kcal', 0, type=float),
                "carb_g": request.form.get('breakfast-carb_g', 0, type=float),
                "protein_g": request.form.get('breakfast-protein_g', 0, type=float),
                "fat_g": request.form.get('breakfast-fat_g', 0, type=float),
                "free_sugar_g": request.form.get('breakfast-free_sugar_g', 0, type=float),
                "fibre_g": request.form.get('breakfast-fibre_g', 0, type=float),
                "sodium_mg": request.form.get('breakfast-sodium_mg', 0, type=float),
                "calcium_mg": request.form.get('breakfast-calcium_mg', 0, type=float),
                "iron_mg": request.form.get('breakfast-iron_mg', 0, type=float),
                "vitamin_c_mg": request.form.get('breakfast-vitamin_c_mg', 0, type=float),
                "folate_ug": request.form.get('breakfast-folate_ug', 0, type=float)
            },
            "lunch": {
                "kcal": request.form.get('lunch-kcal', 0, type=float),
                "carb_g": request.form.get('lunch-carb_g', 0, type=float),
                "protein_g": request.form.get('lunch-protein_g', 0, type=float),
                "fat_g": request.form.get('lunch-fat_g', 0, type=float),
                "free_sugar_g": request.form.get('lunch-free_sugar_g', 0, type=float),
                "fibre_g": request.form.get('lunch-fibre_g', 0, type=float),
                "sodium_mg": request.form.get('lunch-sodium_mg', 0, type=float),
                "calcium_mg": request.form.get('lunch-calcium_mg', 0, type=float),
                "iron_mg": request.form.get('lunch-iron_mg', 0, type=float),
                "vitamin_c_mg": request.form.get('lunch-vitamin_c_mg', 0, type=float),
                "folate_ug": request.form.get('lunch-folate_ug', 0, type=float)
            },
            "dinner": {
                "kcal": request.form.get('dinner-kcal', 0, type=float),
                "carb_g": request.form.get('dinner-carb_g', 0, type=float),
                "protein_g": request.form.get('dinner-protein_g', 0, type=float),
                "fat_g": request.form.get('dinner-fat_g', 0, type=float),
                "free_sugar_g": request.form.get('dinner-free_sugar_g', 0, type=float),
                "fibre_g": request.form.get('dinner-fibre_g', 0, type=float),
                "sodium_mg": request.form.get('dinner-sodium_mg', 0, type=float),
                "calcium_mg": request.form.get('dinner-calcium_mg', 0, type=float),
                "iron_mg": request.form.get('dinner-iron_mg', 0, type=float),
                "vitamin_c_mg": request.form.get('dinner-vitamin_c_mg', 0, type=float),
                "folate_ug": request.form.get('dinner-folate_ug', 0, type=float)
            }
            # Add "snacks" here if you track them
        }
        
        plan_title = request.form.get('plan_title', 'Custom Plan')

        # 2. Use the upsert function (no change needed here)
        upsert_nutrition_plan(mother_id, plan_title, required_nutrients)

        flash(f"Nutrition plan for {mother.get('name')} updated successfully!", "success")
        return redirect(url_for('doctor_patient_profile', mother_id=mother_id))

    # === GET Request: Show the form (no change needed here) ===
    today = datetime.now().strftime("%Y-%m-%d")
    active_plan = get_active_plan_for_mother_and_date(mother_id, today)
    
    return render_template("doctor_profile.html", 
                           mother=mother, 
                           plan=active_plan, # This is her saved plan (or None)
                           presets=json.dumps(RDA_PRESETS) # Pass presets as JSON
                          )
@app.route("/api/mothers/assigned/<doctor_id>", methods=["GET"])
def get_assigned_mothers_api(doctor_id):
    # Security check: Ensure the requesting user is the doctor whose ID is being queried (or an admin)
    if session.get('role') != 'doctor' or session.get('user_id') != doctor_id:
        return jsonify({"error": "Unauthorized access"}), 403

    mothers = get_assigned_mothers(doctor_id)
    return jsonify(mothers)
@app.route("/api/doctor/<doctor_id>", methods=["GET"])
def get_doctor_details(doctor_id):
    try:
        doctor = users_col.find_one({"_id": ObjectId(doctor_id), "role": "doctor"}, 
                                    {"name": 1, "email": 1, "location": 1}) # Only project safe fields
        
        if doctor:
            doctor['_id'] = str(doctor['_id'])
            return jsonify(doctor)
        
        return jsonify({"error": "Doctor not found"}), 404
    except Exception:
        return jsonify({"error": "Invalid Doctor ID"}), 400
    


@app.route("/query", methods=["GET", "POST"])
def query_page():
    # Only logged-in mothers may post queries here
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'mother':
        return redirect(url_for('login'))

    if request.method == 'POST':
        subject = request.form.get('subject')
        message = request.form.get('message')
        mother_id = session.get('user_id') or request.form.get('motherId')

        if not subject or not message or not mother_id:
            error = "Subject and message are required."
            return render_template('query.html', error=error, mother_id=mother_id)

        # Save query in `queries` collection
        from models import db
        query_doc = {
            "motherId": mother_id,
            "subject": subject,
            "message": message,
            "status": "open",
            "createdAt": datetime.utcnow()
        }
        try:
            db.get_collection('queries').insert_one(query_doc)
        except Exception as e:
            error = f"Could not save query: {e}"
            return render_template('query.html', error=error, mother_id=mother_id)

        return render_template('query.html', success=True, mother_id=mother_id)

    return render_template('query.html', mother_id=session.get('user_id'))

# API: upload meal (mother)
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

    # Create meal record
    meal_id, _ = create_meal_doc(mother_id, meal_type, meal_date, save_path)

    # Run dummy OCR
    ocr_result = analyze_image_dummy(save_path)
    print(ocr_result)
    dish_name = ocr_result["nutrients"]["dish_name"]
    nutrients = {k: v for k, v in ocr_result["nutrients"].items() if k != "dish_name"}



    # Update the meal document
    updated = update_meal_labels_and_nutrients(meal_id, ocr_result.get("labels"), nutrients, dish_name)

    updated['_id'] = str(updated['_id'])

    # --- Compare with doctor's plan ---
    from models import get_active_plan_for_mother_and_date, create_alert
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

# Calculate total daily goal (sum of required_nutrients across all meal types)
    if plan and plan.get("required_nutrients"):
        daily_goal = {}
        for meal_type_data in plan["required_nutrients"].values():
            for k, v in meal_type_data.items():
                daily_goal[k] = daily_goal.get(k, 0) + v
    else:   
        daily_goal = {}

# Compute remaining nutrients
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

# API: doctor creates nutrition plan
@app.route("/api/nutrition-plans", methods=["POST"])
def create_plan_api():
    data = request.get_json() or {}
    mother_id = data.get("motherId")
    title = data.get("title", "Daily Nutrition Plan")
    required_nutrients = data.get("required_nutrients", {})  # new field

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
    from models import meals_col
    meals = list(meals_col.find({"motherId": mother_id}).sort("mealDate", -1))
    for m in meals:
        m["_id"] = str(m["_id"])
    return jsonify(meals)

@app.route("/api/alerts/<mother_id>", methods=["GET"])
def get_alerts_for_mother(mother_id):
    from models import get_active_alerts
    alerts = get_active_alerts(mother_id)
    return jsonify(alerts)

# API: Get all queries (for doctor)
@app.route("/api/queries", methods=["GET"])
def get_all_queries():
    if session.get('role') != 'doctor':
        return jsonify({"error": "Unauthorized"}), 403
    
    from models import db
    queries = list(db.get_collection('queries').find().sort("createdAt", -1))
    for q in queries:
        q["_id"] = str(q["_id"])
    return jsonify(queries)

# API: Get queries for a specific mother
@app.route("/api/queries/mother/<mother_id>", methods=["GET"])
def get_mother_queries(mother_id):
    from models import db
    queries = list(db.get_collection('queries').find({"motherId": mother_id}).sort("createdAt", -1))
    for q in queries:
        q["_id"] = str(q["_id"])
    return jsonify(queries)

# API: Remaining nutrients for the day
@app.route("/api/nutrients/remaining/<mother_id>", methods=["GET"])
def get_remaining_nutrients(mother_id):
    
    print("isi")
    today = datetime.now().strftime("%Y-%m-%d")

    # 1️⃣ Get active plan for the mother
    plan = get_active_plan_for_mother_and_date(mother_id, today)
    print(plan)
    if not plan or not plan.get("required_nutrients"):
        return jsonify({"error": "No active plan found for today"}), 404

    # 2️⃣ Calculate total daily goal (sum of all meals)
    daily_goal = {}
    for meal_type_data in plan["required_nutrients"].values():
        for k, v in meal_type_data.items():
            daily_goal[k] = daily_goal.get(k, 0) + v
    print(daily_goal)
    # 3️⃣ Get total intake for the day
    total_intake = get_total_intake_for_day(mother_id, today)

    # 4️⃣ Compute remaining
    remaining = {}
    for k, goal in daily_goal.items():
        taken = total_intake.get(k, 0)
        remaining[k] = round(max(goal - taken, 0), 2)
    print(remaining)
    print("haha")
    return jsonify({
        "date": today,
        "required": daily_goal,
        "consumed": total_intake,
        "remaining": remaining
    })


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

