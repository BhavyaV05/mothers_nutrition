from datetime import datetime

class Meal:
    def __init__(self, mother_id, meal_type, meal_date, image_url=None):
        self.mother_id = mother_id
        self.meal_type = meal_type
        self.meal_date = meal_date
        self.image_url = image_url
        self.nutrients = self._placeholder_ocr()
        self.created_at = datetime.utcnow()
    
    def _placeholder_ocr(self):
        """
        Placeholder for OCR function - returns dummy nutrition data
        In real implementation, this would analyze the meal image
        """
        return {
            "kcal": 350,
            "protein_g": 12,
            "carbs_g": 45,
            "fat_g": 14,
            "confidence": 0.85
        }
    
    def to_dict(self):
        return {
            "mother_id": self.mother_id,
            "meal_type": self.meal_type,
            "meal_date": self.meal_date,
            "image_url": self.image_url,
            "nutrients": self.nutrients,
            "created_at": self.created_at
        }