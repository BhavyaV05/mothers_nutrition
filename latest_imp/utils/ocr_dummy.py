import random

def analyze_image_dummy(image_path):

    # List of 10 hardcoded food items in required format
    food_data = [
        {
            "dish_name": "Hot tea (Garam Chai)",
            "kcal": 16.14, "carb_g": 2.58, "protein_g": 0.39, "fat_g": 0.53,
            "free_sugar_g": 2.58, "fibre_g": 0, "sodium_mg": 3.12, 
            "calcium_mg": 14.2, "iron_mg": 0.02, "vitamin_c_mg": 0.5, "folate_ug": 1.8
        },
        {
            "dish_name": "Instant Coffee",
            "kcal": 100 , "carb_g": 80, "protein_g": 0.64, "fat_g": 0.75,
            "free_sugar_g": 3.62, "fibre_g": 0, "sodium_mg": 4.92, 
            "calcium_mg": 20.87, "iron_mg": 0.06, "vitamin_c_mg": 1.51, "folate_ug": 5.6
        },
        {
            "dish_name": "Espresso Coffee",
            "kcal": 51.54, "carb_g": 6.62, "protein_g": 1.75, "fat_g": 2.14,
            "free_sugar_g": 6.53, "fibre_g": 0, "sodium_mg": 13.98, 
            "calcium_mg": 58.1, "iron_mg": 0.15, "vitamin_c_mg": 1.51, "folate_ug": 5.53
        },
        {
            "dish_name": "Iced Tea",
            "kcal": 10.34, "carb_g": 2.7, "protein_g": 0.03, "fat_g": 0.01,
            "free_sugar_g": 2.7, "fibre_g": 0, "sodium_mg": 0.23, 
            "calcium_mg": 1.18, "iron_mg": 0.02, "vitamin_c_mg": 5.95, "folate_ug": 1.28
        },
        {
            "dish_name": "Aam Panna (Raw Mango Drink)",
            "kcal": 35.92, "carb_g": 9.05, "protein_g": 0.16, "fat_g": 0.03,
            "free_sugar_g": 7.49, "fibre_g": 0.61, "sodium_mg": 79.82, 
            "calcium_mg": 7.08, "iron_mg": 0.14, "vitamin_c_mg": 45.3, "folate_ug": 14.05
        },
        {
            "dish_name": "Masala Dosa",
            "kcal": 168, "carb_g": 25, "protein_g": 4, "fat_g": 5,
            "free_sugar_g": 1, "fibre_g": 1.5, "sodium_mg": 180,
            "calcium_mg": 15, "iron_mg": 0.7, "vitamin_c_mg": 1, "folate_ug": 22
        },
        {
            "dish_name": "Paneer Butter Masala",
            "kcal": 320, "carb_g": 14, "protein_g": 12, "fat_g": 24,
            "free_sugar_g": 4, "fibre_g": 2.2, "sodium_mg": 450,
            "calcium_mg": 210, "iron_mg": 1.2, "vitamin_c_mg": 3, "folate_ug": 18
        },
        {
            "dish_name": "Upma",
            "kcal": 205, "carb_g": 32, "protein_g": 5, "fat_g": 6,
            "free_sugar_g": 2, "fibre_g": 3, "sodium_mg": 310,
            "calcium_mg": 25, "iron_mg": 1.1, "vitamin_c_mg": 0.4, "folate_ug": 35
        },
        {
            "dish_name": "Rajma Chawal",
            "kcal": 350, "carb_g": 60, "protein_g": 14, "fat_g": 6,
            "free_sugar_g": 3, "fibre_g": 8, "sodium_mg": 420,
            "calcium_mg": 62, "iron_mg": 2.7, "vitamin_c_mg": 9, "folate_ug": 80
        },
        {
            "dish_name": "Roti",
            "kcal": 120, "carb_g": 18, "protein_g": 3, "fat_g": 2,
            "free_sugar_g": 0.5, "fibre_g": 2.8, "sodium_mg": 5,
            "calcium_mg": 10, "iron_mg": 0.6, "vitamin_c_mg": 0.2, "folate_ug": 20
        }
    ]

    # Pick one randomly
    selected = random.choice(food_data)

    # Construct final result JSON
    result = {
        "labels": {
            "tags": ["veg", "home-cooked"],
            "confidence": round(random.uniform(0.80, 0.98), 2)
        },
        "nutrients": selected,
        "recognized_text": f"Recognized Dish: {selected['dish_name']}"
    }

    return result
