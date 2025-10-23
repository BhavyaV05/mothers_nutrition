from flask import Blueprint, request, current_app, jsonify
from middleware.auth_middleware import verify_token
import uuid

plans_bp = Blueprint("plans", __name__)

@plans_bp.route("/", methods=["POST"])
@verify_token(allowed_roles=("doctor","admin"))
def create_plan():
    db = current_app.config["DB"]
    data = request.json or {}
    if not data.get("motherId") or not data.get("title"):
        return jsonify({"error": "motherId and title required"}), 400
    plan = {
        "_id": str(uuid.uuid4()),
        "motherId": data["motherId"],
        "title": data["title"],
        "meals": data.get("meals", []),
        "status": data.get("status", "active")
    }
    db.plans.insert_one(plan)
    return jsonify({"planId": plan["_id"], "status": plan["status"]}), 201

@plans_bp.route("/<plan_id>", methods=["GET"])
@verify_token()
def get_plan(plan_id):
    db = current_app.config["DB"]
    p = db.plans.find_one({"_id": plan_id})
    if not p:
        return jsonify({"error": "plan not found"}), 404
    p["planId"] = p["_id"]
    del p["_id"]
    return jsonify(p)
