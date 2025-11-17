# In app.py (find your existing upload_meal route)

@app.route("/api/meals/upload", methods=["POST"])
def upload_meal():
    # ... (keep all your existing code for upload, OCR, etc.) ...
    
    plan = get_active_plan_for_mother_and_date(mother_id, meal_date)
    alert_info = None
    meal_recommendation = None 

    if plan and plan.get("required_nutrients") and meal_type in plan["required_nutrients"]:
        target_nutrients = plan["required_nutrients"][meal_type]
        deficits = compare_nutrients(actual_nutrients, target_nutrients)
        
        if deficits:
            # --- A. DEFICIT FOUND ---
            
            # Part 1: Save Alert (you already have this)
            alert_doc = create_alert(...)
            alert_info = {"alert_created": True, ...}

            # Part 2: Generate Recommendation (you already have this)
            mother_doc = get_user_by_id(mother_id)
            # ... (rest of your recommendation logic) ...
            
            # ===--- START: THIS IS THE NEW CODE TO ADD ---===
            
            # 1. Get Doctor and Asha Worker IDs from the mother's document
            doctor_id = mother_doc.get("assigned_doctor_id")
            asha_worker_id = mother_doc.get("assigned_asha_worker_id")
            mother_name = mother_doc.get("name", "a patient")

            # 2. Create the URL for the new report page
            #    We use _external=True to get the full URL (e.g., http://...)
            report_url = url_for('generate_mother_report', mother_id=mother_id, _external=True)

            # 3. Create the notification message
            message = f"Nutrient deficit detected for {mother_name} after her {meal_type}."
            
            # 4. Send notifications
            create_notification(doctor_id, message, report_url)
            create_notification(asha_worker_id, message, report_url)
            
            # ===--- END: NEW CODE ---===
        
        else:
            alert_info = {"alert_created": False}
    else:
        alert_info = {"alert_created": False, "reason": "no plan for meal type"}

    # ... (keep your 'users_col.update_one' logic) ...
    # ... (keep your 'total_intake', 'daily_goal', 'remaining' logic) ...
    
    return jsonify({
        # ... (keep your existing JSON response) ...
    }), 201