# In utils/nutrient_mapper.py (a new file)

# 1. Maps your app's short keys (from plan/OCR) to the recommender's
#    full-name keys (from its CSV file).
SHORT_TO_LONG_MAP = {
    "kcal": "Calories (kcal)",
    "carb_g": "Carbohydrates (g)",
    "protein_g": "Protein (g)",
    "fat_g": "Fats (g)",
    "free_sugar_g": "Free Sugar (g)",
    "fibre_g": "Fibre (g)",
    "sodium_mg": "Sodium (mg)",
    "calcium_mg": "Calcium (mg)",
    "iron_mg": "Iron (mg)",
    "vitamin_c_mg": "Vitamin C (mg)",
    "folate_ug": "Folate (µg)"
}

# 2. Maps the recommender's full-name keys to the text query
#    it expects (e.g., "low in protein").
#    This is based on your recommender's NUTRIENT_MAP, but reversed.
LONG_TO_QUERY_MAP = {
    "Protein (g)": "protein",
    "Iron (mg)": "iron",
    "Calcium (mg)": "calcium",
    "Fats (g)": "fat",
    "Fibre (g)": "fiber",
    "Carbohydrates (g)": "carbohydrate",
    "Free Sugar (g)": "sugar",
    "Vitamin C (mg)": "vitamin c",
    "Folate (µg)": "folate"
    # Note: 'sodium', 'kcal' are missing from your recommender's
    # original NUTRIENT_MAP, so we can't search for "low in sodium".
}

def deficits_to_text_query(deficits: dict) -> str:
    """
    Translates a deficit dictionary (e.g., {"protein_g": 10})
    into a text string (e.g., "Low in protein").
    """
    low_in_terms = []
    
    for short_key, deficit_amount in deficits.items():
        # Step 1: "protein_g" -> "Protein (g)"
        long_key = SHORT_TO_LONG_MAP.get(short_key)
        if not long_key:
            continue
            
        # Step 2: "Protein (g)" -> "protein"
        query_term = LONG_TO_QUERY_MAP.get(long_key)
        if not query_term:
            continue
            
        if query_term not in low_in_terms:
            low_in_terms.append(query_term)
            
    if not low_in_terms:
        return "" # No deficits found that match the recommender's terms

    # Build the final string: "Low in protein and iron"
    query = "Low in " + " and ".join(low_in_terms)
    print(query)
    return query