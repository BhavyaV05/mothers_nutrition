import os
from flask import Flask, jsonify
from dotenv import load_dotenv
from pymongo import MongoClient
from routes.auth import auth_bp
from routes.mothers import mothers_bp
from routes.meals import meals_bp
from routes.plans import plans_bp
from routes.alerts import alerts_bp
from routes.stats import stats_bp
from utils.seed import seed_demo_data

load_dotenv()
app = Flask(__name__)

# Mongo client (single global used by route modules)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "nutrition_tracker")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]

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
    return jsonify({"service": "Mother Nutrition Tracker API", "status": "ok"})

if __name__ == "__main__":
    # Seed demo data if not present
    seed_demo_data(db)
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=int(os.getenv("FLASK_DEBUG", "0")))
