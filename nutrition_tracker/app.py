import os
from flask import Flask, jsonify, render_template, request, flash, redirect, url_for, session
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from bson import ObjectId
from functools import wraps
from routes.auth import auth_bp
from routes.mothers import mothers_bp
from routes.meals import meals_bp
from routes.plans import plans_bp
from routes.alerts import alerts_bp
from routes.stats import stats_bp
from utils.seed import seed_demo_data

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")  # Change this in production

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Mongo client (single global used by route modules)
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "nutrition_tracker")

# Create MongoDB client with server API version
try:
    mongo_client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
    # Verify connection with ping
    mongo_client.admin.command('ping')
    print("Successfully connected to MongoDB Atlas!")
    db = mongo_client[DB_NAME]
except Exception as e:
    print(f"Error connecting to MongoDB Atlas: {e}")
    raise

# make db accessible to blueprints via app config
app.config["DB"] = db

# Register blueprints
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(mothers_bp, url_prefix="/api/mothers")
app.register_blueprint(meals_bp, url_prefix="/api/meals")
app.register_blueprint(plans_bp, url_prefix="/api/nutrition-plans")
app.register_blueprint(alerts_bp, url_prefix="/api/alerts")
app.register_blueprint(stats_bp, url_prefix="/api/stats")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        mother_data = {
            "name": request.form["name"],
            "phone": request.form["phone"],
            "expected_delivery_date": datetime.strptime(request.form["expected_delivery_date"], "%Y-%m-%d"),
            "parity": int(request.form["parity"]),
            "address": request.form["address"],
            "risk_status": "normal",
            "created_at": datetime.utcnow()
        }
        
        result = db.mothers.insert_one(mother_data)
        flash(f"Registration successful! Your ID is: {result.inserted_id}", "success")
        return redirect(url_for("log_meal"))
    
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form["phone"]
        name = request.form["name"]
        
        mother = db.mothers.find_one({
            "phone": phone,
            "name": name
        })
        
        if mother:
            session['user_id'] = str(mother['_id'])
            session['user_name'] = mother['name']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route("/log-meal", methods=["GET", "POST"])
@login_required
def log_meal():
    if request.method == "POST":
        try:
            mother_id = ObjectId(session['user_id'])
            
            meal_data = {
                "mother_id": str(mother_id),
                "meal_type": request.form["meal_type"],
                "meal_date": datetime.strptime(request.form["meal_date"], "%Y-%m-%d"),
                "image_url": None,  # TODO: Implement image upload
                "nutrients": {
                    "kcal": 350,  # Placeholder values
                    "protein_g": 12,
                    "carbs_g": 45,
                    "fat_g": 14
                },
                "created_at": datetime.utcnow()
            }
            
            db.meals.insert_one(meal_data)
            flash("Meal logged successfully!", "success")
            return redirect(url_for("history"))
            
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("log_meal"))
    
    return render_template("log_meal.html")

@app.route("/history")
@login_required
def history():
    mother_id = session['user_id']
    meals = []
    mother = None
    
    if mother_id:
        try:
            mother = db.mothers.find_one({"_id": ObjectId(mother_id)})
            if mother:
                meals = list(db.meals.find({"mother_id": mother_id}).sort("meal_date", -1))
                
                # Calculate averages
                if meals:
                    avg_calories = sum(meal["nutrients"]["kcal"] for meal in meals) / len(meals)
                    avg_protein = sum(meal["nutrients"]["protein_g"] for meal in meals) / len(meals)
                else:
                    avg_calories = avg_protein = 0
                    
                return render_template("history.html", 
                    meals=meals,
                    mother_id=mother_id,
                    avg_calories=round(avg_calories, 1),
                    avg_protein=round(avg_protein, 1),
                    risk_status=mother["risk_status"]
                )
            else:
                flash("Mother ID not found", "danger")
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
    
    return render_template("history.html", meals=None, mother_id=mother_id)

if __name__ == "__main__":
    # Seed demo data if not present
    seed_demo_data(db)
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=int(os.getenv("FLASK_DEBUG", "0")))
