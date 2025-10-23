def ocr_placeholder():
    """
    Simple placeholder simulating OCR/model result.
    Replace this function to call real OCR / food recognition API.
    """
    return {
        "labels": {"tags": ["veg", "home-cooked"], "confidence": 0.91},
        "nutrients": {"kcal": 310, "protein_g": 10, "carb_g": 45, "fat_g": 9}
    }
