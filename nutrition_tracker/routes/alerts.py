from flask import Blueprint, request, current_app, jsonify
from middleware.auth_middleware import verify_token
import uuid, datetime

alerts_bp = Blueprint("alerts", __name__)

@alerts_bp.route("/", methods=["GET"])
@verify_token()
def list_alerts():
    db = current_app.config["DB"]
    query = {}
    motherId = request.args.get("motherId")
    if motherId:
        query["motherId"] = motherId
    alerts = list(db.alerts.find(query))
    for a in alerts:
        a["alertId"] = a["_id"]; del a["_id"]
    return jsonify(alerts)

@alerts_bp.route("/", methods=["POST"])
@verify_token()
def create_alert():
    db = current_app.config["DB"]
    data = request.json or {}
    if not data.get("motherId") or not data.get("message"):
        return jsonify({"error": "motherId and message required"}), 400
    alert = {
        "_id": str(uuid.uuid4()),
        "motherId": data["motherId"],
        "type": data.get("type", "adherence"),
        "severity": data.get("severity", "medium"),
        "message": data["message"],
        "created_at": datetime.datetime.utcnow()
    }
    db.alerts.insert_one(alert)
    return jsonify({"alertId": alert["_id"], "status": "created"}), 201
