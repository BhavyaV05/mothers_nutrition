from flask import Flask, jsonify
from pymongo import MongoClient
import os

app = Flask(__name__)

# --- Database Setup ---

# Set your connection string (replace with your actual string)
# It's best practice to store this in an environment variable
CONNECTION_STRING = "mongodb+srv://radha:#R08032005r@cluster0.xk7lsaf.mongodb.net/mothers_nutrition?appName=Cluster0"

# Connect to MongoDB
client = MongoClient(CONNECTION_STRING)

# Get the database (it will be created if it doesn't exist)
# This is where you name your database "mothers_nutrition"
db = client.mothers_nutrition

# --- Your Flask Routes ---

@app.route('/')
def home():
    return "Welcome to the Mother's Nutrition App!"

@app.route('/test_db')
def test_db():
    try:
        # Get the 'recipes' collection (it will be created if it doesn't exist)
        recipes_collection = db.recipes
        
        # Insert a sample document to create the db and collection
        recipes_collection.insert_one({
            "name": "Sample Recipe",
            "ingredients": ["Spinach", "Feta"]
        })
        
        return "Database connection successful! Added a sample recipe."
    except Exception as e:
        return f"Database connection failed: {e}"

if __name__ == '__main__':
    app.run(debug=True)