# app.py
from fastapi import FastAPI
from pydantic import BaseModel
from meal_recommender.meal_recommender import generate_recommendations

app = FastAPI(title="Mother Nutrition Planner - Meal Recommender API")

class MotherProfile(BaseModel):
    state: str
    area: str
    income_range: str
    diet_pref: str

class RecommendationRequest(BaseModel):
    doctor_suggestion: str
    mother_profile: MotherProfile

@app.post("/recommend_meals")
def recommend_meals(req: RecommendationRequest):
    result = generate_recommendations(req.doctor_suggestion, req.mother_profile.dict())
    return result

@app.get("/")
def home():
    return {"message": "Welcome to the Mother Nutrition Planner Recommendation API"}
