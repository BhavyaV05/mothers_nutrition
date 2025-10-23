from flask import Blueprint, request, current_app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from middleware.auth_middleware import generate_token
import uuid

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Registers a user: body = { "name", "phone", "password", "role" }
    role: mother | asha | doctor | admin
    """
    db = current_app.config["DB"]
    data = request.json or {}
    name = data.get("name")
    phone = data.get("phone")
    password = data.get("password")
    role = data.get("role", "mother")

    if not (name and phone and password):
        return jsonify({"error": "name, phone and password required"}), 400

    users = db.users
    if users.find_one({"phone": phone}):
        return jsonify({"error": "phone already registered"}), 400

    user = {
        "_id": str(uuid.uuid4()),
        "name": name,
        "phone": phone,
        "password_hash": generate_password_hash(password),
        "role": role
    }
    users.insert_one(user)
    token = generate_token(user_id=user["_id"], role=role, name=name)
    return jsonify({"access_token": token, "user": {"id": user["_id"], "role": role, "name": name}}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login: { "phone", "password" }
    """
    db = current_app.config["DB"]
    data = request.json or {}
    phone = data.get("phone")
    password = data.get("password")
    if not (phone and password):
        return jsonify({"error": "phone and password required"}), 400

    users = db.users
    user = users.find_one({"phone": phone})
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "invalid credentials"}), 401

    token = generate_token(user_id=user["_id"], role=user.get("role", "mother"), name=user.get("name"))
    return jsonify({"access_token": token, "user": {"id": user["_id"], "role": user.get("role"), "name": user.get("name")}})

@auth_bp.route("/me", methods=["GET"])
def me():
    """
    Simple token-based 'me' endpoint; expects Authorization header and returns decoded payload
    """
    from middleware.auth_middleware import decode_token
    auth = request.headers.get("Authorization", "")
    if not auth:
        return jsonify({"error": "Authorization header missing"}), 401
    try:
        token = auth.split()[1]
        payload = decode_token(token)
        return jsonify(payload)
    except Exception as e:
        return jsonify({"error": "Invalid token", "detail": str(e)}), 401
