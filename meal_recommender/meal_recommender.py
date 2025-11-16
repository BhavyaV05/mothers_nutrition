import json
import os
import numpy as np
import pandas as pd
import csv
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv  # <-- NEW: Import to load .env file

# --- Load Environment Variables ---
# This line reads your .env file (like the one you provided)
# and loads its variables into os.environ
load_dotenv()

# --- Updated File Paths ---
CLASSIFICATION_DATA_FILE = "./data/food-mother-classified-2.csv"
NUTRITION_DATA_FILE = "./data/Indian_Food_Nutrition_Processed.csv"

# ----------------------------------------------------------------
# MongoDB Connection Setup
# ----------------------------------------------------------------
# MONGO_URI is now loaded from your .env file
MONGO_URI = os.environ.get("MONGO_URI") 
# DB_NAME is taken from the MONGO_URI you provided
DB_NAME = "mothers_nutrition"
# This is the collection where recommendations will be saved
COLLECTION_NAME = "recommendations" 

if not MONGO_URI:
    print("Error: MONGO_URI not found. Make sure it's in your .env file.")
    client = None
    db = None
    collection = None
else:
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        # Test connection
        client.server_info()
        print(f"Successfully connected to MongoDB: {DB_NAME}.{COLLECTION_NAME}")
    except Exception as e:
        print(f"Error: Could not connect to MongoDB. {e}")
        print("Please check your MONGO_URI, password, and network/firewall access.")
        client = None
        db = None
        collection = None

# ----------------------------------------------------------------
# Nutrient columns (from Indian_Food_Nutrition_Processed.csv)
# ----------------------------------------------------------------
NUTRIENT_COLS = [
    "Calories (kcal)", "Carbohydrates (g)", "Protein (g)", "Fats (g)",
    "Free Sugar (g)", "Fibre (g)", "Sodium (mg)", "Calcium (mg)",
    "Iron (mg)", "Vitamin C (mg)", "Folate (µg)"
]

# ----------------------------------------------------------------
# Keyword mapping for deficiencies
# ----------------------------------------------------------------
NUTRIENT_MAP = {
    "protein": "Protein (g)",
    "iron": "Iron (mg)",
    "calcium": "Calcium (mg)",
    "fat": "Fats (g)",
    "fiber": "Fibre (g)",
    "fibre": "Fibre (g)",
    "carbohydrate": "Carbohydrates (g)",
    "sugar": "Free Sugar (g)",
    "vitamin c": "Vitamin C (mg)",
    "folate": "Folate (µg)"
}

# ----------------------------------------------------------------
# Parse doctor deficiency notes
# ----------------------------------------------------------------
def parse_deficiency(text: str):
    text = text.lower()
    vec = {n: 0 for n in NUTRIENT_COLS}
    for key, col in NUTRIENT_MAP.items():
        # Goal: increase this nutrient
        if f"low in {key}" in text or f"lacking {key}" in text:
            vec[col] = 1
        # Goal: decrease this nutrient
        if f"avoid {key}" in text or f"high in {key}" in text:
            vec[col] = -1
    return vec


# ----------------------------------------------------------------
# Generate personalized meal recommendations
# ----------------------------------------------------------------
def generate_recommendations(deficiency_text, profile, top_n=5):
    """
    Generates meal recommendations and saves the result to MongoDB.
    """
    # --- Load BOTH CSV files ---
    try:
        df_nutri = pd.read_csv(NUTRITION_DATA_FILE, encoding='utf-8-sig')
    except FileNotFoundError as e:
        return {"error": f"Data file not found. Make sure both CSVs exist. Missing file: {e.filename}"}

    try:
        with open(CLASSIFICATION_DATA_FILE, 'r', encoding='utf-8-sig') as fh:
            reader = csv.reader(fh)
            rows = [r for r in reader if any(cell.strip() for cell in r)]
    except FileNotFoundError as e:
        return {"error": f"Data file not found. Make sure both CSVs exist. Missing file: {e.filename}"}

    if not rows:
        return {"error": f"{CLASSIFICATION_DATA_FILE} is empty or unreadable."}

    header = rows[0]
    num_cols = len(header)
    parsed = []
    for r in rows[1:]:
        if len(r) == num_cols:
            parsed.append(r)
            continue
        if len(r) > num_cols:
            if len(r) >= 6:
                first_five = r[0:5]
                middle_parts = r[5:-1]
                cuisine = ";".join([p for p in middle_parts if p is not None and p != ""]) or r[5]
                last = r[-1]
                new_row = first_five + [cuisine, last]
                parsed.append(new_row)
            continue
        if len(r) < num_cols:
            new_row = r + [''] * (num_cols - len(r))
            parsed.append(new_row)

    df_class = pd.DataFrame(parsed, columns=[c.strip() for c in header])

    # --- Clean column headers ---
    df_class.columns = df_class.columns.str.strip(' "')
    df_nutri.columns = df_nutri.columns.str.strip(' "')

    if 'Dish Name' not in df_class.columns:
        return {"error": f"'Dish Name' column not found in {CLASSIFICATION_DATA_FILE}. Check file."}
    if 'Dish Name' not in df_nutri.columns:
        return {"error": f"'Dish Name' column not found in {NUTRITION_DATA_FILE}. Check file."}
        
    df_class['Dish Name'] = df_class['Dish Name'].str.strip(' "')
    df_nutri['Dish Name'] = df_nutri['Dish Name'].str.strip(' "')

    # --- Merge the two dataframes on 'Dish Name' ---
    df = pd.merge(df_nutri, df_class, on="Dish Name", how="inner")

    if df.empty:
        return {"error": "No dishes found in common between nutrition and classification files. Check 'Dish Name' consistency."}
    
    # --- Rename columns to simplified form ---
    df = df.rename(columns={
        "States (Commonly Found In)": "states",
        "Area Type (Rural/Urban/Both)": "area",
        "Diet Type": "diet_type",
        "Income Range (Commonly Consumed By)": "income_range",
        "Cuisine Type": "cuisine",
        "Known Allergens": "allergens"
    })

    # --- Check for Nutrient Columns ---
    missing_nutrient_cols = [col for col in NUTRIENT_COLS if col not in df.columns]
    if missing_nutrient_cols:
        return {"error": f"Missing required nutrient columns after merge: {missing_nutrient_cols}. Check {NUTRITION_DATA_FILE}."}

    # Normalize nutrient columns
    for col in NUTRIENT_COLS:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna(subset=NUTRIENT_COLS)
    if df.empty:
        return {"error": "All merged dishes have missing or non-numeric nutrient data; cannot compute recommendations."}

    scaler = MinMaxScaler()
    nutrients_scaled = scaler.fit_transform(df[NUTRIENT_COLS])
    df_norm = df.copy()
    for i, col in enumerate(NUTRIENT_COLS):
        df_norm[col] = nutrients_scaled[:, i]

    # Build deficiency vector
    def_vec = np.array([list(parse_deficiency(deficiency_text).values())])
    food_vecs = df_norm[NUTRIENT_COLS].values
    nutrient_scores = cosine_similarity(def_vec, food_vecs)[0]
    df_norm["nutrient_score"] = nutrient_scores

    # --- UPDATED Filter by mother's profile ---
    def matches(profile, row):
        state_ok = "All Indian States" in str(row["states"]) or profile["state"] in str(row["states"])
        area_ok = row["area"].lower() in ["both", profile["area"].lower()]
        diet_ok = profile["diet_pref"].lower() in str(row["diet_type"]).lower()
        income_ok = any(rng in str(row["income_range"]) for rng in profile["income_range"].split(","))
        cuisine_ok = profile.get("cuisine_pref", "").lower() in str(row["cuisine"]).lower()
        
        allergies_ok = True
        if profile.get("allergies_to_avoid"):
            allergies_ok = all(
                allergy.lower() not in str(row["allergens"]).lower() 
                for allergy in profile["allergies_to_avoid"]
            )
        return state_ok and area_ok and diet_ok and income_ok and cuisine_ok and allergies_ok

    df_filtered = df_norm[df_norm.apply(lambda r: matches(profile, r), axis=1)]
    if df_filtered.empty:
        return {"error": "No matching meals found for this profile. Try adjusting filters (e.g., state, cuisine, allergies)."}

    df_filtered["final_score"] = df_filtered["nutrient_score"] 
    top_meals = df_filtered.sort_values("final_score", ascending=False).head(top_n)

    output_columns = [
        "Dish Name", "states", "diet_type", "cuisine", 
        "allergens", "income_range", "final_score"
    ]
    
    result = {
        "deficiencies": [k for k, v in parse_deficiency(deficiency_text).items() if v == 1],
        "avoidances": [k for k, v in parse_deficiency(deficiency_text).items() if v == -1],
        "recommended_meals": top_meals[output_columns].to_dict(orient="records"),
        "summary": "Recommended meals tailored to nutrient deficiencies and the mother's context."
    }

    # --- NEW: Save result to MongoDB ---
    if collection is not None:
        try:
            document_to_save = result.copy()
            document_to_save['user_profile'] = profile
            document_to_save['deficiency_query'] = deficiency_text
            document_to_save['created_at'] = datetime.utcnow() 

            insert_result = collection.insert_one(document_to_save)
            result['mongo_id'] = str(insert_result.inserted_id)
        except Exception as e:
            print(f"Error: Failed to write recommendation to MongoDB. {e}")
            result['mongo_id'] = None
    else:
        print("Warning: MongoDB client not connected. Skipping database insert.")
        result['mongo_id'] = None
    
    return result

# --- No more __main__ block ---
# This file is now a module, meant to be imported by your backend.