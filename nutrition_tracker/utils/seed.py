import datetime
import uuid

def seed_demo_data(db):
    # Only seed once
    if db.users.count_documents({}) > 0:
        return

    # Users
    u1 = {"_id": str(uuid.uuid4()), "name": "Aarti Devi", "phone": "+919900000001", "password_hash": "seeded", "role": "mother"}
    u2 = {"_id": str(uuid.uuid4()), "name": "Dr. Rao", "phone": "+919900000002", "password_hash": "seeded", "role": "doctor"}
    u3 = {"_id": str(uuid.uuid4()), "name": "ASHA Rekha", "phone": "+919900000003", "password_hash": "seeded", "role": "asha"}
    db.users.insert_many([u1,u2,u3])

    # Mothers
    m1 = {"_id":"m_1","name":"Aarti Devi","expectedDeliveryDate":"2026-02-10","parity":1,"address":"Hyderabad","risk":"medium","assigned_asha":u3["_id"]}
    m2 = {"_id":"m_2","name":"Sita Rani","expectedDeliveryDate":"2026-04-05","parity":0,"address":"Warangal","risk":"normal","assigned_asha":u3["_id"]}
    db.mothers.insert_many([m1,m2])

    # Plans
    p1 = {"_id":"p_1","motherId":"m_1","title":"2nd Trimester Starter","meals":[{"day":"Mon","time":"08:00","name":"Upma","kcal":320,"protein_g":10}],"status":"active"}
    db.plans.insert_one(p1)

    # Meals (seed)
    meal = {"_id":"meal_1","motherId":"m_1","mealType":"breakfast","mealDate":datetime.datetime.utcnow().isoformat(),"nutrients":{"kcal":310,"protein_g":12,"carb_g":45,"fat_g":9},"labels":{"tags":["veg"],"confidence":0.9},"created_at":datetime.datetime.utcnow()}
    db.meals.insert_one(meal)

    # Alerts and admin stats
    db.alerts.insert_one({"_id":"a_1","motherId":"m_1","type":"adherence","severity":"medium","message":"Missed 2 meals yesterday","created_at":datetime.datetime.utcnow()})
    db.admin_stats.insert_one({"totalMothers":25,"activePlans":18,"avgCalorieIntake":1850,"proteinDeficiencyCases":6,"adherenceRate":"82%", "seeded_at": datetime.datetime.utcnow()})
