# gemini_food_classifier.py
import os
import json
import pandas as pd
from tqdm import tqdm
from time import sleep
from dotenv import load_dotenv
import google.generativeai as genai

# -----------------------------
# Setup
# -----------------------------
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

INPUT_CSV = "./data/Indian_Food_Nutrition_Processed.csv"
OUTPUT_CSV = "./data/Indian_Food_Nutrition_Tagged.csv"
CACHE_FILE = "./data/gemini_cache.json"

# -----------------------------
# Load cache to avoid re-billing
# -----------------------------
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        CACHE = json.load(f)
else:
    CACHE = {}

# -----------------------------
# Gemini prompt template
# -----------------------------
PROMPT_TEMPLATE = """Given the Indian dish name: "{food}".
Classify it as follows:
1. List of Indian states or UTs where this food is commonly consumed.
2. Whether it is more popular in rural, urban, or both areas.
3. The dietary category it fits best: [Vegetarian, Non-Vegetarian, Eggitarian].
4. The typical income ranges that can afford this food: ["<1L","1-3L","3-6L",">6L"].

Return only a JSON object like this:
{{
  "states": ["State1","State2"],
  "area": "rural/urban/both",
  "diet_type": "Vegetarian",
  "income_range": ["1-3L","3-6L"]
}}"""

# -----------------------------
# Gemini classification function
# -----------------------------
def classify_food(food_name: str):
    if food_name in CACHE:
        return CACHE[food_name]

    try:
        response = genai.GenerativeModel("gemini-1.5-flash").generate_content(
            PROMPT_TEMPLATE.format(food=food_name)
        )
        text = response.text.strip()
        result = json.loads(text)
        CACHE[food_name] = result
        with open(CACHE_FILE, "w") as f:
            json.dump(CACHE, f, indent=2)
        sleep(1)
        return result
    except Exception as e:
        print(f"[WARN] Failed for {food_name}: {e}")
        return {
            "states": [],
            "area": "",
            "diet_type": "",
            "income_range": []
        }

# -----------------------------
# Run classifier
# -----------------------------
def main():
    df = pd.read_csv(INPUT_CSV)
    results = []

    for food in tqdm(df["Food_Item"], desc="Classifying foods"):
        res = classify_food(food)
        results.append(res)

    meta_df = pd.DataFrame(results)
    final_df = pd.concat([df, meta_df], axis=1)
    final_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Saved enriched dataset to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
