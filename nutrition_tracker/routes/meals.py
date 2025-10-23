from flask import Blueprint, request, current_app, jsonify
from middleware.auth_middleware import verify_token
from utils.ocr_placeholder import ocr_placeholder
import uuid, datetime

meals_bp = Blueprint("meals", __name__)

@meals_bp.route("/upload", methods=["POST"])
@verify_token()
def upload_meal():
    """
    Expects JSON for prototype:
    { "motherId", "mealType", "mealDate", "image_url" (optional) }
    (In production use multipart/form-data and upload to object storage)
    """
    db = current_app.config["DB"]
    data = request.json or {}
    mother_id = data.get("motherId")
    if not mother_id:
        return jsonify({"error": "motherId required"}), 400

    # OCR placeholder (simulate classification + nutrient extraction)
    ocr_result = ocr_placeholder()

    meal = {
        "_id": str(uuid.uuid4()),
        "motherId": mother_id,
        "mealType": data.get("mealType", "unknown"),
        "mealDate": data.get("mealDate", datetime.datetime.utcnow().isoformat()),
        "image_url": data.get("image_url"),
        "nutrients": ocr_result["nutrients"],
        "labels": ocr_result["labels"],
        "created_at": datetime.datetime.utcnow()
    }
    db.meals.insert_one(meal)
    # convert _id to mealId for response
    meal_id = meal["_id"]
    return jsonify({
        "mealId": meal_id,
        "image_url": meal.get("image_url"),
        "nutrients": meal["nutrients"],
        "labels": meal["labels"]
    }), 201

@meals_bp.route("/<meal_id>", methods=["GET"])
@verify_token()
def get_meal(meal_id):
    db = current_app.config["DB"]
    m = db.meals.find_one({"_id": meal_id})
    if not m:
        return jsonify({"error": "meal not found"}), 404
    m["mealId"] = m["_id"]
    del m["_id"]
    return jsonify(m)
