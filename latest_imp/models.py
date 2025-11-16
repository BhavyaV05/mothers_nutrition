from pymongo import MongoClient
from config import MONGO_URI
from bson.objectid import ObjectId
from datetime import datetime
from pymongo import ReturnDocument
client = MongoClient(MONGO_URI)
db = client.get_default_database()

meals_col = db.get_collection("meals")
plans_col = db.get_collection("nutrition_plans")
# mothers_col = db.get_collection("mothers")
users_col = db.get_collection("users")
def get_user_by_email_and_role(email, role):
    """Find a user by email and role for login authentication."""
    user = users_col.find_one({"email": email, "role": role})
    # NOTE: You must verify the password hash in app.py after fetching the user.
    return user
def get_user_by_id(user_id):
    """Fetch a user document by their ObjectId."""
    try:
        return users_col.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None

def get_total_intake_for_day(mother_id, meal_date):
    """Return the total nutrients consumed by a mother on a given day."""
    meals = list(db.meals.find({"motherId": mother_id, "mealDate": meal_date}))
    total = {}

    for meal in meals:
        nutrients = meal.get("nutrients", {})
        for k, v in nutrients.items():
            try:
                value = float(v)
            except (ValueError, TypeError):
                continue  # skip dish_name or any accidental non-numeric value

            total[k] = total.get(k, 0) + value

    return {k: round(v, 2) for k, v in total.items()}

def create_meal_doc(mother_id, meal_type, meal_date, image_path):
    doc = {
        "motherId": mother_id,
        "mealType": meal_type,
        "mealDate": meal_date,
        "image_path": image_path,
        "status": "pending",
        "createdAt": datetime.utcnow()
    }
    res = meals_col.insert_one(doc)
    return str(res.inserted_id), doc

def update_meal_labels_and_nutrients(meal_id, labels, nutrients, dish_name):
    updated_meal = meals_col.find_one_and_update(
        {"_id": ObjectId(meal_id)},
        {"$set": {
            "labels": labels,
            "nutrients": nutrients,
            "dish_name": dish_name,          # <--- NEW FIELD STORED
            "status": "processed",
            "processedAt": datetime.utcnow()
        }},
        return_document=ReturnDocument.AFTER
    )
    return updated_meal

def get_meal(meal_id):
    return meals_col.find_one({"_id": ObjectId(meal_id)})

def create_nutrition_plan(mother_id, title, meals):
    doc = {
        "motherId": mother_id,
        "title": title,
        "meals": meals,
        "status": "active",
        "createdAt": datetime.utcnow()
    }
    res = plans_col.insert_one(doc)
    return str(res.inserted_id), doc
def get_latest_plan_for_mother(mother_id):
    plan = plans_col.find_one({"motherId": mother_id, "status": "active"}, sort=[("createdAt", -1)])
    return plan

def get_total_nutrients_for_day(mother_id, meal_date):
    """Sum nutrients from all meals uploaded by mother on a given date."""
    meals = list(meals_col.find({"motherId": mother_id, "mealDate": meal_date, "status": "processed"}))
    totals = {"kcal": 0, "protein_g": 0, "carb_g": 0, "fat_g": 0}
    for m in meals:
        n = m.get("nutrients") or {}
        for key in totals:
            totals[key] += n.get(key, 0)
    return totals



def create_alert(mother_id, meal_date, nutrient_deficit, reason=None):
    """Insert a nutrient alert with optional reason and return serialized alert."""
    alert = {
        "motherId": mother_id,
        "mealDate": meal_date,
        "nutrient_deficit": nutrient_deficit,
        "status": "active",
        "createdAt": datetime.utcnow()
    }

    if reason:
        alert["reason"] = reason

    res = db.alerts.insert_one(alert)
    alert["_id"] = str(res.inserted_id)  # Convert ObjectId to string before returning

    return alert


def get_active_alerts(mother_id):
    alerts = list(db.alerts.find({"motherId": mother_id, "status": "active"}).sort("createdAt", -1))
    for a in alerts:
        a["_id"] = str(a["_id"])
    return alerts
def get_active_plan_for_mother_and_date(mother_id, meal_date):
    """Return the latest active plan for a mother for the given date."""
    plan = plans_col.find_one(
        {"motherId": mother_id, "status": "active"},
        sort=[("createdAt", -1)]
    )
    return plan

# --- ASHA helper functions ---

def assign_mother_to_asha(asha_id, mother_id):
    doc = {"ashaId": asha_id, "motherId": mother_id, "assignedAt": datetime.utcnow(), "active": True}
    res = db.asha_assignments.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc

def get_mothers_for_asha(asha_id):
    assignments = list(db.asha_assignments.find({"ashaId": asha_id, "active": True}))
    mother_ids = [a["motherId"] for a in assignments]
    mothers = list(users_col.find({"_id": {"$in": [ObjectId(mid) for mid in mother_ids]}}))
    for m in mothers:
        m["_id"] = str(m["_id"])
    return mothers

def create_visit_record(asha_id, mother_id, visit_date, visit_type, observations=None, metrics=None, photos=None, related_alert=None):
    doc = {
        "ashaId": asha_id,
        "motherId": mother_id,
        "visitDate": visit_date,
        "type": visit_type,
        "observations": observations or "",
        "metrics": metrics or {},
        "photos": photos or [],
        "relatedAlertId": related_alert,
        "status": "completed" if visit_type=="spot-check" else "open",
        "createdAt": datetime.utcnow()
    }
    res = db.visits.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc

def get_visits_for_mother(mother_id, limit=50):
    visits = list(db.visits.find({"motherId": mother_id}).sort("createdAt", -1).limit(limit))
    for v in visits:
        v["_id"] = str(v["_id"])
    return visits

def get_active_alerts_for_asha(asha_id):
    # returns alerts for assigned mothers
    assignments = list(db.asha_assignments.find({"ashaId": asha_id, "active": True}))
    mother_ids = [a["motherId"] for a in assignments]
    alerts = list(db.alerts.find({"motherId": {"$in": mother_ids}, "status": "active"}).sort("createdAt", -1))
    for a in alerts:
        a["_id"] = str(a["_id"])
    return alerts

def triage_alert(alert_id, asha_id, action, notes=None, escalate_to_doctor=False):
    update = {"$set": {"triagedBy": asha_id, "triageNotes": notes, "escalated": escalate_to_doctor}}
    if action == "resolve":
        update["$set"]["status"] = "resolved"
    elif action == "ack":
        update["$set"]["status"] = "acknowledged"
    updated = db.alerts.find_one_and_update({"_id": ObjectId(alert_id)}, update, return_document=ReturnDocument.AFTER)
    if updated:
        updated["_id"] = str(updated["_id"])
    return updated
