from flask import Blueprint, request, current_app, jsonify
from middleware.auth_middleware import verify_token
import uuid

mothers_bp = Blueprint("mothers", __name__)

@mothers_bp.route("/", methods=["GET"])
@verify_token(allowed_roles=None)  # any authenticated user
def list_mothers():
    db = current_app.config["DB"]
    mothers = list(db.mothers.find({}, {"_id": 1, "name": 1, "risk": 1, "assigned_asha": 1}))
    # convert _id to id
    for m in mothers:
        m["id"] = m["_id"]
        del m["_id"]
    return jsonify(mothers)

@mothers_bp.route("/", methods=["POST"])
@verify_token()
def add_mother():
    db = current_app.config["DB"]
    data = request.json or {}
    if not data.get("name") or not data.get("expectedDeliveryDate"):
        return jsonify({"error": "name and expectedDeliveryDate required"}), 400
    mother = {
        "_id": str(uuid.uuid4()),
        "name": data["name"],
        "phone": data.get("phone"),
        "expectedDeliveryDate": data["expectedDeliveryDate"],
        "parity": data.get("parity", 0),
        "address": data.get("address"),
        "risk": data.get("risk", "normal"),
        "assigned_asha": data.get("assigned_asha")
    }
    db.mothers.insert_one(mother)
    return jsonify({"motherId": mother["_id"], "status": "registered"}), 201

@mothers_bp.route("/<mother_id>", methods=["GET"])
@verify_token()
def get_mother(mother_id):
    db = current_app.config["DB"]
    mother = db.mothers.find_one({"_id": mother_id})
    if not mother:
        return jsonify({"error": "mother not found"}), 404
    mother["id"] = mother["_id"]
    del mother["_id"]
    return jsonify(mother)
