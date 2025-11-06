# meal_recommender.py
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------
# Config
# -----------------------------
TAGGED_CSV = "./data/Indian_Food_Nutrition_Tagged.csv"

NUTRIENT_COLS = [
    "Energy", "Protein", "Iron", "Calcium", "Fat", "Fibre", "Carbohydrates"
]

# -----------------------------
# Parse deficiency keywords
# -----------------------------
NUTRIENT_MAP = {
    "protein": "Protein",
    "iron": "Iron",
    "calcium": "Calcium",
    "fat": "Fat",
    "fibre": "Fibre",
    "fiber": "Fibre",
    "carbohydrate": "Carbohydrates",
    "sugar": "Carbohydrates"
}

def parse_deficiency(text: str):
    text = text.lower()
    vec = {n: 0 for n in NUTRIENT_COLS}
    for key, col in NUTRIENT_MAP.items():
        if f"low in {key}" in text or f"lacking {key}" in text:
            vec[col] = 1
        if f"avoid {key}" in text or f"high in {key}" in text:
            vec[col] = -1
    return vec

# -----------------------------
# Generate recommendations
# -----------------------------
def generate_recommendations(deficiency_text, profile, top_n=5):
    df = pd.read_csv(TAGGED_CSV)
    scaler = MinMaxScaler()
    nutrients_scaled = scaler.fit_transform(df[NUTRIENT_COLS])
    df_norm = df.copy()
    for i, col in enumerate(NUTRIENT_COLS):
        df_norm[col] = nutrients_scaled[:, i]

    def_vec = np.array([list(parse_deficiency(deficiency_text).values())])
    food_vecs = df_norm[NUTRIENT_COLS].values
    nutrient_scores = cosine_similarity(def_vec, food_vecs)[0]
    df_norm["nutrient_score"] = nutrient_scores

    # Contextual filters
    def matches(profile, row):
        state_ok = (profile["state"] in str(row["states"])) if "states" in row else True
        area_ok = (row.get("area") in ["both", profile["area"]])
        diet_ok = (row.get("diet_type","").lower() in profile["diet_pref"].lower())
        income_ok = any(rng in str(row.get("income_range","")) for rng in profile["income_range"].split(","))
        return state_ok and area_ok and diet_ok and income_ok

    df_filtered = df_norm[df_norm.apply(lambda r: matches(profile, r), axis=1)]

    # Scoring
    df_filtered["final_score"] = (
        0.5 * df_filtered["nutrient_score"] +
        0.15 * 1 +
        0.1 * 1 +
        0.1 * 1 +
        0.15 * 1
    )

    top_meals = df_filtered.sort_values("final_score", ascending=False).head(top_n)

    result = {
        "deficiencies": [k for k, v in parse_deficiency(deficiency_text).items() if v == 1],
        "recommended_meals": top_meals[["Food_Item", "states", "diet_type", "income_range", "final_score"]].to_dict(orient="records"),
        "summary": "Recommended meals tailored to nutrient deficiencies and profile."
    }
    return result

# -----------------------------
# Example run
# -----------------------------
if __name__ == "__main__":
    example_def = "Low in iron and calcium, avoid fatty foods."
    example_profile = {
        "state": "Karnataka",
        "area": "rural",
        "income_range": "1-3L",
        "diet_pref": "vegetarian"
    }
    recs = generate_recommendations(example_def, example_profile, top_n=5)
    print(json.dumps(recs, indent=2))
