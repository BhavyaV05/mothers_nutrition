import json
import numpy as np
import pandas as pd
import csv
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

# --- Updated File Paths ---
CLASSIFICATION_DATA_FILE = "./data/food-mother-classified-2.csv"
NUTRITION_DATA_FILE = "./data/Indian_Food_Nutrition_Processed.csv"

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
    # --- Load BOTH CSV files ---
    try:
        # Load nutrition file normally
        df_nutri = pd.read_csv(NUTRITION_DATA_FILE, encoding='utf-8-sig')
    except FileNotFoundError as e:
        return {"error": f"Data file not found. Make sure both CSVs exist. Missing file: {e.filename}"}

    # --- Robust parsing for classification CSV using csv.reader ---
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
        # If the row has exactly the right number of columns, keep as-is
        if len(r) == num_cols:
            parsed.append(r)
            continue

        # If row has more columns than header, merge middle extra columns
        # into the 'Cuisine Type' column (assumed index 5) and keep last
        # column as 'Known Allergens' (assumed last index).
        if len(r) > num_cols:
            # Ensure we have at least the first 5 fields and the last field
            if len(r) >= 6:
                first_five = r[0:5]
                middle_parts = r[5:-1]
                # join middle parts using semicolon to keep similar format
                cuisine = ";".join([p for p in middle_parts if p is not None and p != ""]) or r[5]
                last = r[-1]
                new_row = first_five + [cuisine, last]
                parsed.append(new_row)
                continue

        # If row has fewer columns, pad with empty strings
        if len(r) < num_cols:
            new_row = r + [''] * (num_cols - len(r))
            parsed.append(new_row)

    # Build DataFrame
    df_class = pd.DataFrame(parsed, columns=[c.strip() for c in header])

    # --- FIX: Clean column headers *immediately* after loading ---
    # This strips BOTH spaces and quote characters (") from the ends of column names
    df_class.columns = df_class.columns.str.strip(' "')
    df_nutri.columns = df_nutri.columns.str.strip(' "')

    # Clean 'Dish Name' *content*
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
    # This now includes the new columns
    df = df.rename(columns={
        "States (Commonly Found In)": "states",
        "Area Type (Rural/Urban/Both)": "area",
        "Diet Type": "diet_type",
        "Income Range (Commonly Consumed By)": "income_range",
        "Cuisine Type": "cuisine",
        "Known Allergens": "allergens"
    })

    # --- Check for Nutrient Columns AFTER renaming/cleaning ---
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
        # Handle "All Indian States" as a universal match
        state_ok = "All Indian States" in str(row["states"]) or profile["state"] in str(row["states"])
        area_ok = row["area"].lower() in ["both", profile["area"].lower()]
        diet_ok = profile["diet_pref"].lower() in str(row["diet_type"]).lower()
        income_ok = any(rng in str(row["income_range"]) for rng in profile["income_range"].split(","))
        
        # --- NEW FILTERS ---
        # Check if the preferred cuisine is in the dish's cuisine list
        cuisine_ok = profile.get("cuisine_pref", "").lower() in str(row["cuisine"]).lower()
        
        # Check that none of the user's allergies are in the dish's allergen list
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

    # Weighted scoring
    df_filtered["final_score"] = df_filtered["nutrient_score"] 

    top_meals = df_filtered.sort_values("final_score", ascending=False).head(top_n)

    # --- UPDATED Result to include new columns ---
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
    return result


# ----------------------------------------------------------------
# Example run
# ----------------------------------------------------------------
if __name__ == "__main__":
    # Example 1: Original profile
    print("--- RUN 1: Original Profile (No allergy/cuisine filter) ---")
    example_def_1 = "Low in iron and calcium, avoid fatty foods."
    example_profile_1 = {
        "state": "Karnataka",
        "area": "rural",
        "income_range": "1-3L",
        "diet_pref": "vegetarian",
        "cuisine_pref": "North Indian", # This will now be used
        "allergies_to_avoid": [] # No allergies
    }
    recs = generate_recommendations(example_def_1, example_profile_1, top_n=5)
    print(json.dumps(recs, indent=2))
    
    print("\n" + "="*40 + "\n")

    # Example 2: Profile with allergy filter
    print("--- RUN 2: Profile with Dairy Allergy Filter ---")
    example_def_2 = "Low in protein and iron."
    example_profile_2 = {
        "state": "All Indian States and UTs", # Looking for general food
        "area": "both",
        "income_range": "1-3L",
        "diet_pref": "vegetarian",
        "cuisine_pref": "North Indian", # Likes North Indian
        "allergies_to_avoid": ["Dairy"] # <-- KEY FILTER
    }
    recs = generate_recommendations(example_def_2, example_profile_2, top_n=5)
    print(json.dumps(recs, indent=2))