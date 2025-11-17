import os



from flask import Flask, request, jsonify, render_template, redirect, url_for,session,flash
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER, MAX_CONTENT_LENGTH, SECRET_KEY
from models import create_meal_doc, update_meal_labels_and_nutrients, get_meal, create_nutrition_plan, plans_col, get_total_intake_for_day, get_queries_for_mother,get_active_plan_for_mother_and_date, users_col, create_alert, get_active_alerts,get_queries_by_mother, meals_col,get_random_doctor_id,get_assigned_mothers,get_user_by_id, upsert_nutrition_plan,get_unread_notifications, mark_notification_as_read , create_notification,get_assigned_mothers_by_asha_id

from utils.ocr_dummy import analyze_image_dummy
from bson.objectid import ObjectId
from datetime import datetime
import json
import random
from werkzeug.security import generate_password_hash, check_password_hash
from utils.nutrition_check import compare_nutrients # <-- NEW
from meal_recommendor import recommend_from_deficits

# IMPORTANT for ASHA worker feature
from models import db

from presets import RDA_PRESETS

# from routes.auth import auth_bp
from routes.queries import queries_bp, fetch_queries_for_mother_backend  # Import the queries blueprint
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
# Register blueprints
app.register_blueprint(queries_bp)

# Simple pages
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
@app.route("/reports/mother/<string:mother_id>")
def generate_mother_report(mother_id):
    """
    Shows the visual report page for a specific mother.
    """
    if 'user_id' not in session or session.get('role') not in ['doctor', 'asha']:
        flash("You are not authorized to view this report.", "error")
        return redirect(url_for('login'))
        
    mother = get_user_by_id(mother_id)
    if not mother:
        return "Mother not found", 404
        
    meals = list(meals_col.find(
        {"motherId": mother_id, "status": "processed"}
    ).sort("mealDate", 1))
    
    today = datetime.now().strftime("%Y-%m-%d")
    plan = get_active_plan_for_mother_and_date(mother_id, today)
    alerts = get_active_alerts(mother_id)
    
    return render_template("report.html",
                           mother=mother,
                           meals=meals,
                           plan=plan,
                           alerts=alerts,
                           meals_json=json.dumps(meals, default=str),
                           plan_json=json.dumps(plan, default=str)
                           )
@app.route("/api/notifications")
def get_notifications():
    """
    API endpoint to fetch all unread notifications for the
    currently logged-in user (doctor or asha worker).
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    notifications = get_unread_notifications(user_id)
    
    # Convert ObjectId to string for JSON
    for notif in notifications:
        notif["_id"] = str(notif["_id"])
            
    return jsonify(notifications)


@app.route("/api/notifications/mark_read/<string:notification_id>", methods=["POST"])
def mark_notification_read(notification_id):
    """
    API endpoint to mark a notification as 'read'.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    success = mark_notification_as_read(notification_id, user_id)
    
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Notification not found or permission denied"}), 404
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


        if role == 'mother':
            # Mother-specific fields
            assigned_doctor_id = get_random_doctor_id()
            assigned_asha = assign_random_asha()
            if not assigned_doctor_id:
                error = "Cannot register mother: No doctors available for assignment."
                return render_template("signup.html", error=error, states=INDIAN_STATES, incomes=INCOME_RANGES, diets=DIETARY_PREFERENCES)

            # Ensure doctor & asha ids are stored as strings
            assigned_doctor_id_str = str(assigned_doctor_id) if assigned_doctor_id is not None else None
            assigned_asha_str = str(assigned_asha) if assigned_asha is not None else None

            user_doc.update({
                "name": request.form.get("name"),
                "age": request.form.get("age"),
                "gender": request.form.get("gender"),
                "location_state": request.form.get("state"),
                "location_area_type": request.form.get("area_type"),
                "income_range": request.form.get("income"),
                "dietary_preference": request.form.get("diet"),
                "ashaId": assigned_asha_str,
                "assigned_doctor_id": assigned_doctor_id_str,
                "cuisine_preference": request.form.get("cuisine_preference", ""),
                
                # Split comma-separated string into a list
                "allergies": [
                    allergy.strip().lower() for allergy 
                    in request.form.get("allergies", "").split(',') 
                    if allergy.strip()
                ]

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
    # ensure only mothers can open this page
    if session.get('role') != 'mother':
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    # try to fetch the mother's document and extract assigned doctor id
    try:
        mother = get_user_by_id(user_id)  # you already import this helper
    except Exception:
        mother = None

    if not mother:
        # fallback: still render page but without assignment
        return render_template("mother.html", mother_id=user_id, assigned_doctor_id="")

    # The field name you used is 'assigned_doctor_id' in DB (see earlier fix)
    assigned_doc = mother.get("assigned_doctor_id") or mother.get("assigned_doctor") or ""

    # ensure it's a string (template expects a string)
    if assigned_doc is None:
        assigned_doc = ""
    else:
        assigned_doc = str(assigned_doc)

    assigned_asha = mother.get("ashaId") or ""
    print("Assigned ASHA ID:", assigned_asha) 
    if assigned_asha is None:
        assigned_asha = ""
    else:
        assigned_asha = str(assigned_asha)

    return render_template("mother.html", mother_id=user_id, assigned_doctor_id=assigned_doc, assigned_asha_id=assigned_asha)


# -------------------------------------------------
# DOCTOR PAGE
# -------------------------------------------------
@app.route("/doctor")
def doctor_page():
    if session.get('role') != 'doctor':
        return redirect(url_for('login'))
    
    # This page will now list the doctor's assigned mothers
    doctor_id = session['user_id']
    mothers = get_assigned_mothers(doctor_id)
    
    return render_template("doctor.html", 
                           doctor_id=doctor_id, 
                           mothers=mothers)

# In app.py
@app.route("/asha") # Or whatever your main ASHA dashboard route is
def asha_page():
    if session.get('role') != 'asha':
        return redirect(url_for('login'))
    
    asha_id = session['user_id']
    print(asha_id)
    # 1. Get the simple list of mothers
    mothers = get_assigned_mothers_by_asha_id(asha_id)
    print(mothers)
    # 2. Render the dashboard template
    return render_template("asha_worker.html", 
                           asha_id=asha_id,mothers=mothers)
@app.route("/asha/patient/<string:mother_id>")
def asha_patient_profile(mother_id):
    if session.get('role') != 'asha':
        return redirect(url_for('login'))
    print("hehe")    
    asha_id = session['user_id']
    mother = get_user_by_id(mother_id)
    
    # Security check: Make sure this mother is assigned to this asha worker
    if not mother or mother.get("ashaId") != asha_id:
        flash("You are not authorized to view this patient.", "error")
        return redirect(url_for('asha_page'))

    # Get all the details for this mother
    today = datetime.now().strftime("%Y-%m-%d")
    plan = get_active_plan_for_mother_and_date(mother_id, today)
    alerts = get_active_alerts(mother_id) 
    queries = get_queries_for_mother(mother_id) # Assumes you have this function
    print(plan)
    print(alerts)
    print(queries)
    return render_template("asha_patient_profile.html",
                           mother=mother,
                           plan=plan,
                           alerts=alerts,
                           queries=queries
                           )
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
    
    # Fetch queries for this mother assigned to current doctor
    from models import db
    doctor_id = session.get('user_id')
    
    # Debug: Check all queries for this mother
    all_mother_queries = list(db.get_collection('queries').find({"motherId": ObjectId(mother_id)}))
    print(f"DEBUG: Found {len(all_mother_queries)} total queries for mother {mother_id}")
    
    # Fetch queries with both filters
    queries = list(db.get_collection('queries').find({
        "motherId": ObjectId(mother_id),
        "doctorId": ObjectId(doctor_id)
    }).sort("createdAt", -1))
    
    print(f"DEBUG: Found {len(queries)} queries for mother {mother_id} and doctor {doctor_id}")
    if all_mother_queries:
        print(f"DEBUG: Sample query doctorId: {all_mother_queries[0].get('doctorId')}, Expected: {ObjectId(doctor_id)}")
    
    return render_template("doctor_profile.html", 
                           mother=mother, 
                           plan=active_plan, # This is her saved plan (or None)
                           presets=json.dumps(RDA_PRESETS), # Pass presets as JSON
                           queries=queries # Pass queries for this mother
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
    
# In app.py

# In app.py

# In app.py
@app.route("/api/asha/<asha_id>", methods=["GET"])
def get_asha_details(asha_id):
    try:
        from bson.objectid import ObjectId
        
        asha = users_col.find_one(
            {"_id": ObjectId(asha_id), "role": "asha"}
        )
        
        if asha:
            response_data = {
                "name": asha.get("name", "ASHA Worker"),
                "email": asha.get("email", "N/A"), 
            }
            return jsonify(response_data)
        
        return jsonify({"error": "ASHA worker not found or invalid role"}), 404
    
    except Exception as e:
        print(f"Error fetching ASHA details: {e}")
        return jsonify({"error": "Invalid ASHA ID format"}), 400

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

    # 1. Create the initial meal document
    meal_id, _ = create_meal_doc(mother_id, meal_type, meal_date, save_path)

    # 2. Run OCR/AI to get nutrients
    ocr_result = analyze_image_dummy(save_path)
    dish_name = ocr_result["nutrients"]["dish_name"]
    # This is the "actual" nutrients from the meal
    actual_nutrients = {k: v for k, v in ocr_result["nutrients"].items() if k != "dish_name"}

    # 3. Update the meal document with nutrient info
    updated = update_meal_labels_and_nutrients(
        meal_id, 
        ocr_result.get("labels"), 
        actual_nutrients, 
        dish_name
    )
    updated['_id'] = str(updated['_id'])

    # --- 4. START: Alert & Recommendation Logic ---
    plan = get_active_plan_for_mother_and_date(mother_id, meal_date)
    alert_info = None
    meal_recommendation = None # This is what we will show the mother

    if plan and plan.get("required_nutrients") and meal_type in plan["required_nutrients"]:
        # A plan exists for this meal. Let's compare.
        
        # Get the "target" nutrients for this specific meal
        target_nutrients = plan["required_nutrients"][meal_type]
        
        # Compare actual vs. target to find deficits
        deficits = compare_nutrients(actual_nutrients, target_nutrients)
        
        if deficits:
            # --- A. DEFICIT FOUND ---
            print(f"Deficits found for {mother_id}: {deficits}")
            
            # Part 1: Save Alert for Doctor (Backend)
            alert_doc = create_alert(
                mother_id=mother_id,
                meal_date=meal_date,
                nutrient_deficit=deficits
            )
            alert_info = {"alert_created": True, "deficits": deficits, "alert_id": alert_doc["_id"]}

            # Part 2: Generate Recommendation for Mother (Frontend)
            mother_doc = get_user_by_id(mother_id)
            
            # Build the profile your recommender needs
            profile_for_recommender = {
                "mother_id": mother_id,  # NEW: Add mother_id for tracking recommendations
                "state": mother_doc.get("location_state", ""),
                "area": mother_doc.get("location_area_type", "both"),
                "income_range": mother_doc.get("income_range", ""),
                "diet_pref": mother_doc.get("dietary_preference", ""),
                "cuisine_pref": mother_doc.get("cuisine_preference", ""), 
                "allergies_to_avoid": mother_doc.get("allergies", []) 
            }
            
            # Call the recommender with the deficits
            recs = recommend_from_deficits(deficits, profile_for_recommender, top_n=1)
            print("hahah")
            print(recs)
            # Get the top meal
            if recs and recs.get("recommended_meals") and recs["recommended_meals"]:
                meal_recommendation = recs["recommended_meals"][0]
                meal_recommendation["reason"] = f"Your last meal was a bit low on some nutrients."
                print(f"Recommendation generated: {meal_recommendation['Dish Name']}")
            doctor_id = mother_doc.get("assigned_doctor_id")
            asha_worker_id = mother_doc.get("assigned_asha_worker_id")
            mother_name = mother_doc.get("name", "a patient")

            # 2. Create the URL for the new report page
            #    We use _external=True to get the full URL (e.g., http://...)
            report_url = url_for('generate_mother_report', mother_id=mother_id, _external=True)

            # 3. Create the notification message
            message = f"Nutrient deficit detected for {mother_name} after her {meal_type}."
            
            # 4. Send notifications
            create_notification(doctor_id, message, report_url)
            create_notification(asha_worker_id, message, report_url)
            
        else:
            # --- B. NO DEFICIT ---
            # Meal was good, no alert needed.
            alert_info = {"alert_created": False}
            # meal_recommendation stays None
    
    else:
        # --- C. NO PLAN FOUND ---
        # No plan exists for this meal, so we can't compare.
        alert_info = {"alert_created": False, "reason": "no plan for this meal type"}
        # meal_recommendation stays None

    # 5. Save the final recommendation (or None) to the mother's profile
    users_col.update_one(
        {"_id": ObjectId(mother_id)},
        {"$set": {"latest_recommendation": meal_recommendation}}
    )
    # --- END: Alert & Recommendation Logic ---

    # 6. Calculate daily totals (for summary)
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

    # 7. Send the final response
    return jsonify({
        "meal": updated,
        "ocr_result": ocr_result,
        "meal_check": alert_info, # For backend/doctor use
        "next_meal_recommendation": meal_recommendation, # For mother's app
        "daily_summary": {
            "goal": daily_goal,
            "taken_so_far": total_intake,
            "remaining": remaining
        }
    }), 201

  
# @app.route("/doctor/patient/<string:mother_id>", methods=["GET", "POST"])
# def doctor_patient_profile(mother_id):
#     # Security check: Ensure doctor is logged in and assigned this mother
#     if session.get('role') != 'doctor':
#         return redirect(url_for('login'))
        
#     mother = get_user_by_id(mother_id)
#     if not mother or mother.get("assigned_doctor_id") != session.get("user_id"):
#         flash("Unauthorized: You are not assigned to this patient.", "error")
#         return redirect(url_for('doctor_page'))
    
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

# Doctor responds to a query
@app.route("/query/<query_id>/respond", methods=["POST"])
def respond_to_query(query_id):
    if session.get('role') != 'doctor':
        return redirect(url_for('login'))
    
    response_text = request.form.get('response')
    if not response_text:
        flash("Response cannot be empty.", "error")
        return redirect(request.referrer or url_for('doctor_page'))
    
    from models import db
    try:
        db.get_collection('queries').update_one(
            {"_id": ObjectId(query_id)},
            {"$set": {
                "response": response_text,
                "respondedAt": datetime.utcnow(),
                "respondedBy": session.get('user_id'),
                "status": "answered"
            }}
        )
        flash("Response sent successfully!", "success")
    except Exception as e:
        flash(f"Error sending response: {e}", "error")
    
    return redirect(request.referrer or url_for('doctor_page'))

# API: Remaining nutrients for the day
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
    queries = fetch_queries_for_mother_backend(mother_id) # Call the new function
    details["queries"] = queries
    return jsonify(details)


# -------------------------------------------------
# MAIN
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
