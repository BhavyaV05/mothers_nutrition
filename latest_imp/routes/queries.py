"""
Query Routes - Handles queries/messages between mothers and doctors
"""
from flask import Blueprint, request, jsonify, session
from bson.objectid import ObjectId
from datetime import datetime
from models import users_col
from pymongo import MongoClient
from config import MONGO_URI

# Initialize MongoDB connection
client = MongoClient(MONGO_URI)
db = client.get_default_database()
queries_col = db.get_collection("queries")

queries_bp = Blueprint('queries', __name__)
def serialize_query(query):
    """Convert MongoDB query document to JSON-serializable format"""
    if query:
        query['_id'] = str(query['_id'])
        query['motherId'] = str(query['motherId'])
        if query.get('doctorId'):
            query['doctorId'] = str(query['doctorId'])
        # Convert datetime objects to ISO format strings
        if query.get('createdAt'):
            query['createdAt'] = query['createdAt'].isoformat()
        if query.get('replies'):
            for reply in query['replies']:
                if reply.get('repliedAt'):
                    reply['repliedAt'] = reply['repliedAt'].isoformat()
    return query

def fetch_queries_for_mother_backend(mother_id):
    """
    Fetches and serializes all queries for a given mother ID.
    Used by backend routes like api_asha_mother_details.
    """
    try:
        mother_obj_id = ObjectId(mother_id)
    except Exception:
        return []

    query_filter = {"motherId": mother_obj_id}
    
    # Fetch all queries, sorted by creation date
    queries = list(queries_col.find(query_filter).sort("createdAt", -1))
    
    # Serialize results to convert ObjectIds/datetimes to strings
    for query in queries:
        serialize_query(query)
        
    return queries
# ============================================
# MOTHER ENDPOINTS
# ============================================

@queries_bp.route("/api/queries/create", methods=["POST"])
def create_query():
    """
    Create a new query from mother
    Expected JSON:
    {
        "subject": "Query about nutrition",
        "message": "I have a question about...",
        "category": "nutrition" | "health" | "plan" | "general"
    }
    """
    if session.get('role') != 'mother':
        return jsonify({"error": "Only mothers can create queries"}), 403
    
    mother_id = session.get('user_id')
    data = request.get_json() or {}
    
    subject = data.get("subject", "").strip()
    message = data.get("message", "").strip()
    category = data.get("category", "general")
    
    if not subject or not message:
        return jsonify({"error": "Subject and message are required"}), 400
    
    # Validate category
    valid_categories = ["nutrition", "health", "plan", "general"]
    if category not in valid_categories:
        category = "general"
    
    # Get mother details
    mother = users_col.find_one({"_id": ObjectId(mother_id)})
    if not mother:
        return jsonify({"error": "Mother not found"}), 404
    
    # Get assigned doctor ID from mother's profile
    assigned_doctor_id = mother.get("assigned_doctor_id")
    if assigned_doctor_id:
        try:
            assigned_doctor_id = ObjectId(assigned_doctor_id)
        except Exception:
            assigned_doctor_id = None
    
    query_doc = {
        "motherId": ObjectId(mother_id),
        "motherName": mother.get("name", "Unknown"),
        "motherEmail": mother.get("email"),
        "subject": subject,
        "message": message,
        "category": category,
        "status": "pending",  # pending, in-progress, resolved, closed
        "priority": "normal",  # low, normal, high, urgent
        "doctorId": assigned_doctor_id,  # Assigned doctor from mother's profile
        "replies": [],
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }
    
    result = queries_col.insert_one(query_doc)
    query_doc['_id'] = str(result.inserted_id)
    
    return jsonify({
        "success": True,
        "message": "Query created successfully",
        "query": serialize_query(query_doc)
    }), 201


@queries_bp.route("/api/queries/my-queries", methods=["GET"])
def get_my_queries():
    """
    Get all queries created by the logged-in mother
    Query params:
    - status: filter by status (optional)
    - limit: number of results (default: 50)
    """
    if session.get('role') != 'mother':
        return jsonify({"error": "Only mothers can view their queries"}), 403
    
    mother_id = session.get('user_id')
    status_filter = request.args.get('status')
    limit = int(request.args.get('limit', 50))
    
    query_filter = {"motherId": ObjectId(mother_id)}
    if status_filter:
        query_filter["status"] = status_filter
    
    queries = list(queries_col.find(query_filter).sort("createdAt", -1).limit(limit))
    
    for query in queries:
        serialize_query(query)
    
    return jsonify({
        "success": True,
        "count": len(queries),
        "queries": queries
    }), 200


@queries_bp.route("/api/queries/<query_id>", methods=["GET"])
def get_query_details(query_id):
    """
    Get details of a specific query
    Accessible by the mother who created it or any doctor
    """
    user_role = session.get('role')
    user_id = session.get('user_id')
    
    if not user_role or not user_id:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        query = queries_col.find_one({"_id": ObjectId(query_id)})
    except Exception:
        return jsonify({"error": "Invalid query ID"}), 400
    
    if not query:
        return jsonify({"error": "Query not found"}), 404
    
    # Authorization check
    if user_role == 'mother' and str(query['motherId']) != user_id:
        return jsonify({"error": "You can only view your own queries"}), 403
    
    return jsonify({
        "success": True,
        "query": serialize_query(query)
    }), 200


# ============================================
# DOCTOR ENDPOINTS
# ============================================

@queries_bp.route("/api/queries/all", methods=["GET"])
def get_all_queries():
    """
    Get all queries (for doctors)
    Query params:
    - status: filter by status
    - category: filter by category
    - priority: filter by priority
    - limit: number of results (default: 100)
    """
    if session.get('role') != 'doctor':
        return jsonify({"error": "Only doctors can view all queries"}), 403
    
    # Build filter
    query_filter = {}
    
    status = request.args.get('status')
    if status:
        query_filter['status'] = status
    
    category = request.args.get('category')
    if category:
        query_filter['category'] = category
    
    priority = request.args.get('priority')
    if priority:
        query_filter['priority'] = priority
    
    limit = int(request.args.get('limit', 100))
    
    queries = list(queries_col.find(query_filter).sort("createdAt", -1).limit(limit))
    
    for query in queries:
        serialize_query(query)
    
    return jsonify({
        "success": True,
        "count": len(queries),
        "queries": queries
    }), 200


@queries_bp.route("/api/queries/<query_id>/reply", methods=["POST"])
def reply_to_query(query_id):
    """
    Doctor replies to a query
    Expected JSON:
    {
        "message": "Reply message here...",
        "updateStatus": "in-progress" | "resolved" | "closed" (optional)
    }
    """
    if session.get('role') != 'doctor':
        return jsonify({"error": "Only doctors can reply to queries"}), 403
    
    doctor_id = session.get('user_id')
    data = request.get_json() or {}
    
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Reply message is required"}), 400
    
    try:
        query = queries_col.find_one({"_id": ObjectId(query_id)})
    except Exception:
        return jsonify({"error": "Invalid query ID"}), 400
    
    if not query:
        return jsonify({"error": "Query not found"}), 404
    
    # Get doctor details
    doctor = users_col.find_one({"_id": ObjectId(doctor_id)})
    if not doctor:
        return jsonify({"error": "Doctor not found"}), 404
    
    reply_doc = {
        "doctorId": doctor_id,
        "doctorName": doctor.get("name", "Doctor"),
        "message": message,
        "repliedAt": datetime.utcnow()
    }
    
    # Update query
    update_data = {
        "$push": {"replies": reply_doc},
        "$set": {
            "updatedAt": datetime.utcnow(),
            "doctorId": ObjectId(doctor_id)  # Assign doctor if not already assigned
        }
    }
    
    # Update status if provided
    new_status = data.get("updateStatus")
    if new_status in ["in-progress", "resolved", "closed"]:
        update_data["$set"]["status"] = new_status
    elif query['status'] == 'pending':
        # Automatically move to in-progress when doctor first replies
        update_data["$set"]["status"] = "in-progress"
    
    updated_query = queries_col.find_one_and_update(
        {"_id": ObjectId(query_id)},
        update_data,
        return_document=True
    )
    
    return jsonify({
        "success": True,
        "message": "Reply added successfully",
        "query": serialize_query(updated_query)
    }), 200


@queries_bp.route("/api/queries/<query_id>/update-status", methods=["PUT"])
def update_query_status(query_id):
    """
    Update query status (doctor only)
    Expected JSON:
    {
        "status": "pending" | "in-progress" | "resolved" | "closed",
        "priority": "low" | "normal" | "high" | "urgent" (optional)
    }
    """
    if session.get('role') != 'doctor':
        return jsonify({"error": "Only doctors can update query status"}), 403
    
    data = request.get_json() or {}
    new_status = data.get("status")
    new_priority = data.get("priority")
    
    valid_statuses = ["pending", "in-progress", "resolved", "closed"]
    valid_priorities = ["low", "normal", "high", "urgent"]
    
    update_fields = {"updatedAt": datetime.utcnow()}
    
    if new_status and new_status in valid_statuses:
        update_fields["status"] = new_status
    
    if new_priority and new_priority in valid_priorities:
        update_fields["priority"] = new_priority
    
    if len(update_fields) == 1:  # Only updatedAt
        return jsonify({"error": "No valid fields to update"}), 400
    
    try:
        updated_query = queries_col.find_one_and_update(
            {"_id": ObjectId(query_id)},
            {"$set": update_fields},
            return_document=True
        )
    except Exception:
        return jsonify({"error": "Invalid query ID"}), 400
    
    if not updated_query:
        return jsonify({"error": "Query not found"}), 404
    
    return jsonify({
        "success": True,
        "message": "Query updated successfully",
        "query": serialize_query(updated_query)
    }), 200


@queries_bp.route("/api/queries/<query_id>/assign", methods=["PUT"])
def assign_query_to_doctor(query_id):
    """
    Assign query to a specific doctor
    Expected JSON:
    {
        "doctorId": "doctor_user_id"
    }
    """
    if session.get('role') != 'doctor':
        return jsonify({"error": "Only doctors can assign queries"}), 403
    
    data = request.get_json() or {}
    doctor_id = data.get("doctorId")
    
    if not doctor_id:
        return jsonify({"error": "doctorId is required"}), 400
    
    # Verify doctor exists
    doctor = users_col.find_one({"_id": ObjectId(doctor_id), "role": "doctor"})
    if not doctor:
        return jsonify({"error": "Doctor not found"}), 404
    
    try:
        updated_query = queries_col.find_one_and_update(
            {"_id": ObjectId(query_id)},
            {"$set": {
                "doctorId": ObjectId(doctor_id),
                "updatedAt": datetime.utcnow()
            }},
            return_document=True
        )
    except Exception:
        return jsonify({"error": "Invalid query ID"}), 400
    
    if not updated_query:
        return jsonify({"error": "Query not found"}), 404
    
    return jsonify({
        "success": True,
        "message": "Query assigned successfully",
        "query": serialize_query(updated_query)
    }), 200


# ============================================
# COMMON ENDPOINTS
# ============================================

@queries_bp.route("/api/queries/statistics", methods=["GET"])
def get_query_statistics():
    """
    Get statistics about queries
    For mothers: their own query stats
    For doctors: overall stats
    """
    user_role = session.get('role')
    user_id = session.get('user_id')
    
    if not user_role or not user_id:
        return jsonify({"error": "Authentication required"}), 401
    
    if user_role == 'mother':
        # Mother's own statistics
        filter_query = {"motherId": ObjectId(user_id)}
    else:
        # Doctor sees all statistics
        filter_query = {}
    
    total_queries = queries_col.count_documents(filter_query)
    pending = queries_col.count_documents({**filter_query, "status": "pending"})
    in_progress = queries_col.count_documents({**filter_query, "status": "in-progress"})
    resolved = queries_col.count_documents({**filter_query, "status": "resolved"})
    closed = queries_col.count_documents({**filter_query, "status": "closed"})
    
    # Category breakdown
    categories = {}
    for cat in ["nutrition", "health", "plan", "general"]:
        categories[cat] = queries_col.count_documents({**filter_query, "category": cat})
    
    return jsonify({
        "success": True,
        "statistics": {
            "total": total_queries,
            "byStatus": {
                "pending": pending,
                "in-progress": in_progress,
                "resolved": resolved,
                "closed": closed
            },
            "byCategory": categories
        }
    }), 200
