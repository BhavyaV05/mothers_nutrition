import json
import os
import numpy as np
import pandas as pd
import csv
import random
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import MongoClient
from datetime import datetime, timedelta
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

# ----------------------------------------------------------------
# Helper Functions for Variety & Diversity
# ----------------------------------------------------------------
def get_recent_recommendations(mother_id, days=2, limit=5):
    """
    Fetch recent recommendations for a mother from MongoDB.
    Returns a list of dish names recommended in the last N days.
    """
    if collection is None:
        return []
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Find recent recommendations for this mother
        recent_recs = collection.find({
            "user_profile.mother_id": mother_id,
            "created_at": {"$gte": cutoff_date}
        }).sort("created_at", -1).limit(limit)
        
        # Extract dish names from recommended meals
        recent_dishes = []
        for rec in recent_recs:
            if "recommended_meals" in rec:
                for meal in rec["recommended_meals"]:
                    dish_name = meal.get("Dish Name")
                    if dish_name:
                        recent_dishes.append(dish_name)
        
        return recent_dishes
    except Exception as e:
        print(f"Error fetching recent recommendations: {e}")
        return []

def select_diverse_meal(top_meals, recent_dishes, top_n=5):
    """
    Select a meal from top candidates, ensuring variety.
    
    Strategy:
    1. Get top N high-scoring meals
    2. Exclude recently recommended dishes
    3. Use weighted random selection (higher scores = higher probability)
    
    Args:
        top_meals: DataFrame of meals sorted by score
        recent_dishes: List of recently recommended dish names
        top_n: Number of top candidates to consider
    
    Returns:
        Selected meal row as dict
    """
    if top_meals.empty:
        return None
    
    # Get top N candidates
    candidates = top_meals.head(top_n)
    
    # Filter out recent dishes for variety
    if recent_dishes:
        candidates = candidates[~candidates["Dish Name"].isin(recent_dishes)]
    
    # If all top candidates were recent, fall back to original top meals
    if candidates.empty:
        print("[Variety] All top candidates were recently recommended. Using fallback.")
        candidates = top_meals.head(top_n)
    
    # Use weighted random selection based on scores
    # Higher scores get proportionally higher selection probability
    scores = candidates["final_score"].values
    
    # Normalize scores to probabilities (softmax-like approach)
    # Add small epsilon to avoid division by zero
    exp_scores = np.exp(scores - np.max(scores))  # Numerical stability
    probabilities = exp_scores / np.sum(exp_scores)
    
    # Randomly select based on weighted probabilities
    selected_idx = np.random.choice(len(candidates), p=probabilities)
    selected_meal = candidates.iloc[selected_idx]
    
    print(f"[Variety] Selected: {selected_meal['Dish Name']} (score: {selected_meal['final_score']:.3f})")
    print(f"[Variety] Avoided recent dishes: {recent_dishes[:3]}..." if len(recent_dishes) > 3 else f"[Variety] Recent dishes: {recent_dishes}")
    
    return selected_meal.to_dict()

def recommend_from_deficits(deficits: dict, profile: dict, top_n=1):
    """
    New adapter function to generate recommendations from a
    quantitative deficit dictionary.
    """
    print(f"[Recommender] Received deficits: {deficits}")
    print(profile)
    # 1. Translate deficit dict to text query
    #    e.g., {"protein_g": 10} -> "Low in protein"
    deficiency_text = deficits_to_text_query(deficits)
    
    if not deficiency_text:
        print("[Recommender] No translatable deficits. No recommendation.")
        return None
        
    print(f"[Recommender] Translated to query: '{deficiency_text}'")
    
    # 2. Call the existing recommendation function
    #    This re-uses all your complex logic, file loading, and filtering.
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
    
    Implements a two-pass filter: 
    1. Strict (all profile criteria)
    2. Relaxed (enforce only diet and allergies) if strict fails.
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
    
    # --- Two-Pass Filtering Logic Starts Here ---
    
    def get_allergy_ok(profile, row):
        """Helper to check strict allergy constraint."""
        allergies_ok = True
        if profile.get("allergies_to_avoid"):
            allergies_ok = all(
                allergy.lower() not in str(row["allergens"]).lower() 
                for allergy in profile["allergies_to_avoid"]
            )
        return allergies_ok
        
    def matches_strict(profile, row):
        """Pass 1: Checks ALL profile criteria."""
        state_ok = "All Indian States" in str(row["states"]) or profile["state"] in str(row["states"])
        area_ok = row["area"].lower() in ["both", profile["area"].lower()]
        diet_ok = profile["diet_pref"].lower() in str(row["diet_type"]).lower()
        income_ok = any(rng in str(row["income_range"]) for rng in profile["income_range"].split(","))
        cuisine_ok = profile.get("cuisine_pref", "").lower() in str(row["cuisine"]).lower()
        allergies_ok = get_allergy_ok(profile, row)
        return state_ok and area_ok and diet_ok and income_ok and cuisine_ok and allergies_ok

    # --- Pass 1: Strict Filtering ---
    df_filtered = df_norm[df_norm.apply(lambda r: matches_strict(profile, r), axis=1)]

    if df_filtered.empty:
        print("[Recommender] Strict filtering failed. Trying relaxed search...")
        
        # --- Pass 2: Relaxed Filtering (Only enforce Diet and Allergies) ---
        def matches_relaxed(profile, row):
            """Pass 2: Checks only essential criteria (Diet, Area, Allergies)."""
            
            # Diet MUST remain strict for user preference
            diet_ok = profile["diet_pref"].lower() in str(row["diet_type"]).lower()
            
            # Area remains important (e.g., rural vs urban ingredient availability)
            area_ok = row["area"].lower() in ["both", profile["area"].lower()]
            
            # Allergies MUST remain strict for safety
            allergies_ok = get_allergy_ok(profile, row)
            
            # State, Income, and Cuisine filters are ignored in this pass.
            return area_ok and diet_ok and allergies_ok

        df_filtered = df_norm[df_norm.apply(lambda r: matches_relaxed(profile, r), axis=1)]

    # --- Check Pass 2 Results ---
    if df_filtered.empty:
        # If even the relaxed search fails, we can't recommend anything safe.
        return {"error": "No safe meals found, even after relaxing region, income, and cuisine filters. The basic constraints (Diet Type or Allergies) are too restrictive for the nutrient goals."}

    # --- Continue with sorting and output using the best matches found (from Pass 1 or Pass 2) ---
    # Apply cuisine and income preference boosts to final score
    def apply_preference_boosts(row):
        base_score = row["nutrient_score"]
        boosted_score = base_score
        
        # Cuisine preference boost (15%)
        cuisine_pref = profile.get("cuisine_pref", "").lower()
        if cuisine_pref and cuisine_pref in str(row["cuisine"]).lower():
            boosted_score *= 1.15
        
        # Income range boost (10%)
        income_range = profile.get("income_range", "")
        if income_range and any(rng in str(row["income_range"]) for rng in income_range.split(",")):
            boosted_score *= 1.10
        
        # State/regional preference boost (5%)
        state = profile.get("state", "")
        if state and (state in str(row["states"]) or "All Indian States" in str(row["states"])):
            boosted_score *= 1.05
        
        if boosted_score != base_score:
            print(f"[Boost] {row['Dish Name']}: {base_score:.3f} → {boosted_score:.3f}")
        
        return boosted_score
    
    df_filtered = df_filtered.copy()  # Avoid SettingWithCopyWarning
    df_filtered["final_score"] = df_filtered.apply(apply_preference_boosts, axis=1)
    df_filtered = df_filtered.sort_values("final_score", ascending=False)
    
    # --- NEW: Apply Diversity Logic ---
    mother_id = profile.get("mother_id")
    
    if mother_id:
        # Get recent recommendations to avoid repetition
        recent_dishes = get_recent_recommendations(mother_id, days=2, limit=5)
        print(f"[Variety] Recent dishes for mother {mother_id}: {recent_dishes}")
        
        # Select diverse meal using weighted random selection
        selected_meal = select_diverse_meal(df_filtered, recent_dishes, top_n=5)
        
        if selected_meal:
            # Convert single selection to list format for consistency
            recommended_meals = [selected_meal]
        else:
            # Fallback: use traditional top 1
            recommended_meals = df_filtered.head(1).to_dict(orient="records")
    else:
        # No mother_id provided, use traditional approach
        print("[Variety] No mother_id in profile. Using traditional top-N selection.")
        recommended_meals = df_filtered.head(top_n).to_dict(orient="records")
    
    output_columns = [
        "Dish Name", "states", "diet_type", "cuisine", 
        "allergens", "income_range", "final_score"
    ]
    
    # Ensure output columns are present
    for meal in recommended_meals:
        meal_filtered = {k: meal[k] for k in output_columns if k in meal}
        recommended_meals[recommended_meals.index(meal)] = meal_filtered
    
    result = {
        "deficiencies": [k for k, v in parse_deficiency(deficiency_text).items() if v == 1],
        "avoidances": [k for k, v in parse_deficiency(deficiency_text).items() if v == -1],
        "recommended_meals": recommended_meals,
        "summary": "Recommended meals tailored to nutrient deficiencies and the mother's context."
    }

    # --- Loop to add recipe links using Google Search ---
    print("Fetching recipe links using Google Custom Search...")
    for meal in result["recommended_meals"]:
        dish_name = meal["Dish Name"]
        recipe_link = get_recipe_link_google_search(dish_name)
        meal["recipe_link"] = recipe_link
        print(f"  - {dish_name}: {recipe_link}")

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
#     print("\n" + "="*50)
#     print("--- STARTING TEST RUN ---")
#     print("NOTE: This will connect to MongoDB and use your Google Search API quota.")
#     print("="*50 + "\n")

#     # 1. Define the doctor's query (The broad query that failed previously)
#     example_def = "Low in carbohydrate and protein and sugar and fiber and calcium and iron and vitamin c and folate"

#     # 2. Define the user's profile
#     example_profile = {
#         "state": "Maharashtra",
#         "area": "urban",
#         "income_range": "3-6L",
#         "diet_pref": "vegetarian",
#         "cuisine_pref": "North Indian",
#         "allergies_to_avoid": ["Dairy"] # Test the allergy filter
#     }

#     # 3. Call the function
#     print(f"Generating recommendations for: '{example_def}'")
#     recs = generate_recommendations(example_def, example_profile, top_n=3) 

#     # 4. Print the final result
#     print("\n" + "="*50)
#     print("--- TEST RUN COMPLETE ---")
#     print("Final JSON output (as sent to backend and MongoDB):")
#     print(json.dumps(recs, indent=2))
#     print("="*50 + "\n")