import os
import jwt
from functools import wraps
from datetime import datetime, timedelta
from flask import request, jsonify, current_app

JWT_SECRET = os.getenv("JWT_SECRET", "change_this")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", 86400))

def generate_token(user_id: str, role: str, name: str):
    payload = {
        "sub": user_id,
        "role": role,
        "name": name,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(seconds=JWT_EXP_SECONDS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

def verify_token(optional=False, allowed_roles=None):
    """
    Decorator to protect endpoints. If optional=True, request.user may be None.
    allowed_roles: list or tuple of roles allowed (e.g., ("doctor", "asha"))
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth:
                if optional:
                    request.user = None
                    return f(*args, **kwargs)
                return jsonify({"error": "Authorization header missing"}), 401
            parts = auth.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return jsonify({"error": "Invalid Authorization header"}), 401
            token = parts[1]
            try:
                payload = decode_token(token)
                request.user = {
                    "id": payload["sub"],
                    "role": payload.get("role"),
                    "name": payload.get("name")
                }
                if allowed_roles and request.user["role"] not in allowed_roles:
                    return jsonify({"error": "Forbidden"}), 403
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except Exception as e:
                return jsonify({"error": "Invalid token", "detail": str(e)}), 401
            return f(*args, **kwargs)
        return wrapper
    return decorator
