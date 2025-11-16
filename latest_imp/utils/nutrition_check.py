# In utils/nutrition_check.py (a new file)

def compare_nutrients(actual_nutrients: dict, target_nutrients: dict) -> dict:
    """
    Compares actual consumed nutrients against a target plan.

    Returns a dictionary of deficits (e.g., {"protein_g": 10, "iron_mg": 5})
    where the value is the amount *missing*.
    """
    deficits = {}
    
    # Iterate over the doctor's target plan
    for nutrient_key, target_value in target_nutrients.items():
        
        # Get the nutrient from the mother's meal, default to 0
        actual_value = actual_nutrients.get(nutrient_key, 0)
        
        # Calculate the difference
        difference = target_value - actual_value
        
        # If the mother is short (difference > 0), record the deficit
        if difference > 0:
            deficits[nutrient_key] = round(difference, 2)
            
    return deficits