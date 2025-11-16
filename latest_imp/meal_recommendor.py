import json
import os
import numpy as np
import pandas as pd
import csv
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from utils.nutrient_mapper import deficits_to_text_query
# --- NEW: Import Google Custom Search API ---

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Load Environment Variables ---
# This loads .env file for MONGO_URI and Google API keys
load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

CLASSIFICATION_DATA_FILE = os.path.join(PROJECT_ROOT, "data", "food-mother-classified-2.csv")
NUTRITION_DATA_FILE = os.path.join(PROJECT_ROOT, "data", "Indian_Food_Nutrition_Processed.csv")

# ----------------------------------------------------------------
# MongoDB Connection Setup
# ----------------------------------------------------------------
MONGO_URI = os.environ.get("MONGO_URI") 
DB_NAME = "mothers_nutrition"
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
        client.server_info()
        print(f"Successfully connected to MongoDB: {DB_NAME}.{COLLECTION_NAME}")
    except Exception as e:
        print(f"Error: Could not connect to MongoDB. {e}")
        client = None
        db = None
        collection = None

# ----------------------------------------------------------------
# NEW: Google Custom Search API Setup
# ----------------------------------------------------------------
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.environ.get("SEARCH_ENGINE_ID")

if not GOOGLE_API_KEY or not SEARCH_ENGINE_ID:
    print("Warning: GOOGLE_API_KEY or SEARCH_ENGINE_ID not found in .env file. Recipe links will not be fetched.")
    search_service = None
else:
    try:
        # Build the service object
        search_service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        print("Google Custom Search API configured successfully.")
    except Exception as e:
        print(f"Error configuring Google Custom Search API: {e}")
        search_service = None

# ----------------------------------------------------------------
# Nutrient columns
# ----------------------------------------------------------------
NUTRIENT_COLS = [
    "Calories (kcal)", "Carbohydrates (g)", "Protein (g)", "Fats (g)",
    "Free Sugar (g)", "Fibre (g)", "Sodium (mg)", "Calcium (mg)",
    "Iron (mg)", "Vitamin C (mg)", "Folate (µg)"
]

# ----------------------------------------------------------------
# Nutrient Map
# ----------------------------------------------------------------
NUTRIENT_MAP = {
    "protein": "Protein (g)", "iron": "Iron (mg)", "calcium": "Calcium (mg)",
    "fat": "Fats (g)", "fiber": "Fibre (g)", "fibre": "Fibre (g)",
    "carbohydrate": "Carbohydrates (g)", "sugar": "Free Sugar (g)",
    "vitamin c": "Vitamin C (mg)", "folate": "Folate (µg)"
}

# ----------------------------------------------------------------
# Parse doctor deficiency notes
# ----------------------------------------------------------------
def parse_deficiency(text: str):
    text = text.lower()
    vec = {n: 0 for n in NUTRIENT_COLS}
    for key, col in NUTRIENT_MAP.items():
        if f"low in {key}" in text or f"lacking {key}" in text:
            vec[col] = 1
        if f"avoid {key}" in text or f"high in {key}" in text:
            vec[col] = -1
    return vec
def recommend_from_deficits(deficits: dict, profile: dict, top_n=1):
    """
    New adapter function to generate recommendations from a
    quantitative deficit dictionary.
    """
    print(f"[Recommender] Received deficits: {deficits}")
    print(profile)
    # 1. Translate deficit dict to text query
    #    e.g., {"protein_g": 10} -> "Low in protein"
    deficiency_text = deficits_to_text_query(deficits)
    
    if not deficiency_text:
        print("[Recommender] No translatable deficits. No recommendation.")
        return None
        
    print(f"[Recommender] Translated to query: '{deficiency_text}'")
    
    # 2. Call the existing recommendation function
    #    This re-uses all your complex logic, file loading, and filtering.
    try:
        recommendations = generate_recommendations(
            deficiency_text=deficiency_text,
            profile=profile,
            top_n=top_n
        )
        print(recommendations)
        return recommendations
        
    except Exception as e:
        print(f"[Recommender] Error during generation: {e}")
        return {"error": str(e)}
# ----------------------------------------------------------------
# NEW: Function to get recipe link from Google Search
# ----------------------------------------------------------------
def get_recipe_link_google_search(dish_name):
    if not search_service:
        return "Error: Google Search API not configured."

    try:
        query = f"{dish_name} recipe"
        result = search_service.cse().list(
            q=query,
            cx=SEARCH_ENGINE_ID,
            num=1
        ).execute()

        items = result.get('items', [])
        if items:
            link = items[0].get('link')
            return link
        else:
            return "No recipe link found."
            
    except HttpError as e:
        print(f"Error calling Google Search API for '{dish_name}': {e}")
        if e.resp.status == 429:
            return "Error: Daily free query limit (100) likely exceeded."
        return "Error: API call failed (HttpError)."
    except Exception as e:
        print(f"Error during recipe search for '{dish_name}': {e}")
        return "Error: API call failed (Exception)."

# ----------------------------------------------------------------
# Generate personalized meal recommendations
# ----------------------------------------------------------------
def generate_recommendations(deficiency_text, profile, top_n=5):
    """
    Generates meal recommendations, fetches recipe links, and saves to MongoDB.
    """
    try:
        df_nutri = pd.read_csv(NUTRITION_DATA_FILE, encoding='utf-8-sig')
    except FileNotFoundError as e:
        return {"error": f"Data file not found: {e.filename}"}

    try:
        with open(CLASSIFICATION_DATA_FILE, 'r', encoding='utf-8-sig') as fh:
            reader = csv.reader(fh)
            rows = [r for r in reader if any(cell.strip() for cell in r)]
    except FileNotFoundError as e:
        return {"error": f"Data file not found: {e.filename}"}

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
                first_five, middle_parts, last = r[0:5], r[5:-1], r[-1]
                cuisine = ";".join([p for p in middle_parts if p.strip()]) or r[5]
                parsed.append(first_five + [cuisine, last])
            continue
        if len(r) < num_cols:
            parsed.append(r + [''] * (num_cols - len(r)))

    df_class = pd.DataFrame(parsed, columns=[c.strip() for c in header])

    df_class.columns = df_class.columns.str.strip(' "')
    df_nutri.columns = df_nutri.columns.str.strip(' "')

    if 'Dish Name' not in df_class.columns:
        return {"error": f"'Dish Name' column not found in {CLASSIFICATION_DATA_FILE}."}
    if 'Dish Name' not in df_nutri.columns:
        return {"error": f"'Dish Name' column not found in {NUTRITION_DATA_FILE}."}
        
    df_class['Dish Name'] = df_class['Dish Name'].str.strip(' "')
    df_nutri['Dish Name'] = df_nutri['Dish Name'].str.strip(' "')

    df = pd.merge(df_nutri, df_class, on="Dish Name", how="inner")

    if df.empty:
        return {"error": "No dishes found in common between nutrition and classification files."}
    
    df = df.rename(columns={
        "States (Commonly Found In)": "states",
        "Area Type (Rural/Urban/Both)": "area",
        "Diet Type": "diet_type",
        "Income Range (Commonly Consumed By)": "income_range",
        "Cuisine Type": "cuisine",
        "Known Allergens": "allergens"
    })

    missing_nutrient_cols = [col for col in NUTRIENT_COLS if col not in df.columns]
    if missing_nutrient_cols:
        return {"error": f"Missing required nutrient columns: {missing_nutrient_cols}."}

    for col in NUTRIENT_COLS:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna(subset=NUTRIENT_COLS)
    if df.empty:
        return {"error": "All merged dishes have missing or non-numeric nutrient data."}

    scaler = MinMaxScaler()
    nutrients_scaled = scaler.fit_transform(df[NUTRIENT_COLS])
    df_norm = df.copy()
    for i, col in enumerate(NUTRIENT_COLS):
        df_norm[col] = nutrients_scaled[:, i]

    def_vec = np.array([list(parse_deficiency(deficiency_text).values())])
    food_vecs = df_norm[NUTRIENT_COLS].values
    nutrient_scores = cosine_similarity(def_vec, food_vecs)[0]
    df_norm["nutrient_score"] = nutrient_scores

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
        return {"error": "No matching meals found for this profile. Try adjusting filters."}

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

    # --- Loop to add recipe links using Google Search ---
    print("Fetching recipe links using Google Custom Search...")
    for meal in result["recommended_meals"]:
        dish_name = meal["Dish Name"]
        recipe_link = get_recipe_link_google_search(dish_name) # <-- Changed function
        meal["recipe_link"] = recipe_link
        print(f"  - {dish_name}: {recipe_link}")

    # --- Save result to MongoDB ---
    if collection is not None:
        try:
            document_to_save = result.copy()
            document_to_save['user_profile'] = profile
            document_to_save['deficiency_query'] = deficiency_text
            document_to_save['created_at'] = datetime.utcnow() 

            insert_result = collection.insert_one(document_to_save)
            result['mongo_id'] = str(insert_result.inserted_id)
            print(f"Successfully saved recommendation to MongoDB with ID: {result['mongo_id']}")
        except Exception as e:
            print(f"Error: Failed to write recommendation to MongoDB. {e}")
            result['mongo_id'] = None
    else:
        print("Warning: MongoDB client not connected. Skipping database insert.")
        result['mongo_id'] = None
    
    return result


# ----------------------------------------------------------------
# NEW: Example run (for testing)
# ----------------------------------------------------------------
# if __name__ == "__main__":
#     print("\n" + "="*50)
#     print("--- STARTING TEST RUN ---")
#     print("NOTE: This will connect to MongoDB and use your Google Search API quota.")
#     print("="*50 + "\n")

#     # 1. Define the doctor's query
#     example_def = "Low in iron and protein, avoid sugar."

#     # 2. Define the user's profile
#     example_profile = {
#         "state": "Maharashtra",
#         "area": "urban",
#         "income_range": "3-6L",
#         "diet_pref": "vegetarian",
#         "cuisine_pref": "North Indian",
#         "allergies_to_avoid": ["Dairy"] # Test the allergy filter
#     }
    
#     # 3. Call the function
#     # Using top_n=3 to save your free API quota during testing.
#     print(f"Generating recommendations for: '{example_def}'")
#     recs = generate_recommendations(example_def, example_profile, top_n=3) 

#     # 4. Print the final result
#     print("\n" + "="*50)
#     print("--- TEST RUN COMPLETE ---")
#     print("Final JSON output (as sent to backend and MongoDB):")
#     print(json.dumps(recs, indent=2))
#     print("="*50 + "\n")