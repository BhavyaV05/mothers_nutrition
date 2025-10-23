from flask import Blueprint, jsonify, current_app
from middleware.auth_middleware import verify_token

stats_bp = Blueprint("stats", __name__)

@stats_bp.route("/", methods=["GET"])
@verify_token()
def get_stats():
    db = current_app.config["DB"]
    # Try to fetch an admin statistics doc; fall back to hardcoded
    doc = db.admin_stats.find_one({})
    if doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        return jsonify(doc)
    # fallback hardcoded
    stats = {
        "totalMothers": 25,
        "activePlans": 18,
        "avgCalorieIntake": 1850,
        "proteinDeficiencyCases": 6,
        "adherenceRate": "82%"
    }
    return jsonify(stats)
