"""
Placeholder OCR / nutrient-estimation routine.
Returns dummy JSON data simulating OCR + nutrient extraction.
"""

def analyze_image_dummy(image_path):
    # Dummy result -- replace with real OCR/model later
    result = {
        "labels": {
            "tags": ["veg", "home-cooked"],
            "confidence": 0.91
        },
        "nutrients": {
            "kcal": 500,
            "protein_g": 107,
            "carb_g": 100,
            "fat_g": 100
        },
        "recognized_text": "Dummy OCR: Upma ~ 320 kcal"
    }
    return result
