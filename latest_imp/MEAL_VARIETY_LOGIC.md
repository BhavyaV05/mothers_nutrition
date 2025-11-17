# Meal Variety & Diversity Logic

## Problem
The recommendation system was suggesting the same dish repeatedly (e.g., "Boiled rice") because it always selected the highest-scoring meal, even if the mother had just received that recommendation.

## Solution Implemented

### Three-Pronged Approach:

#### 1. **Track Recent Recommendations** 
- Stores the last 5 recommendations in MongoDB with timestamps
- Queries recommendations from the past 2 days
- Function: `get_recent_recommendations(mother_id, days=2, limit=5)`

#### 2. **Filter Out Recent Dishes**
- Excludes recently recommended dishes from the top candidates
- Prevents repetitive suggestions within a 2-day window
- Ensures mothers see variety in their recommendations

#### 3. **Weighted Random Selection**
- Instead of always picking #1, randomly selects from **top 5 candidates**
- Uses **probability-weighted selection**: Higher-scoring meals have higher chances
- Mathematical approach: Softmax probability distribution
  ```
  P(meal_i) = exp(score_i) / Σ exp(score_j)
  ```

### How It Works

```
Step 1: Get top 5 nutritionally suitable meals
        ↓
Step 2: Remove dishes recommended in last 2 days
        ↓
Step 3: Calculate selection probabilities based on scores
        ↓
Step 4: Randomly select using weighted probabilities
        ↓
Result: Nutritious + Varied + User-preferred meals
```

### Example Scenario

**Without Variety Logic:**
- Day 1: Boiled Rice (score: 0.82)
- Day 2: Boiled Rice (score: 0.82)
- Day 3: Boiled Rice (score: 0.82)

**With Variety Logic:**
- Day 1: Boiled Rice (score: 0.82) ← Top scorer
- Day 2: Dal Tadka (score: 0.78) ← Boiled Rice excluded
- Day 3: Palak Paneer (score: 0.75) ← Both previous excluded
- Day 4: Vegetable Pulao (score: 0.81) ← Can get new high scorer
- Day 5: Boiled Rice (score: 0.82) ← Can repeat after 2 days

### Configuration Parameters

You can adjust these in `meal_recommendor.py`:

```python
# In get_recent_recommendations():
days=2          # How many days to look back (default: 2)
limit=5         # Max number of recent dishes to track (default: 5)

# In select_diverse_meal():
top_n=5         # How many top candidates to consider (default: 5)
```

### Benefits

1. **Nutritional Integrity**: Still prioritizes meals that meet nutrient deficiencies
2. **Variety**: Mothers won't see the same dish every day
3. **User Preference**: Higher-scoring meals still have higher selection probability
4. **Fallback Safety**: If all top candidates were recent, falls back to original logic
5. **Adaptable**: Can adjust time windows and candidate pool sizes

### Technical Details

**Files Modified:**
1. `meal_recommendor.py`
   - Added `get_recent_recommendations()` function
   - Added `select_diverse_meal()` function
   - Modified `generate_recommendations()` to use diversity logic
   
2. `app.py`
   - Added `"mother_id"` to `profile_for_recommender`

**Database Schema:**
- Recommendations stored in `recommendations` collection with:
  - `user_profile.mother_id`: Links to specific mother
  - `created_at`: Timestamp for filtering recent recommendations
  - `recommended_meals`: Array of recommended dishes

### Testing

To verify the variety logic is working, check server logs for:
```
[Variety] Recent dishes for mother 691af502d943cee726221d0b: ['Boiled rice (Uble chawal)', ...]
[Variety] Selected: Dal Tadka (score: 0.783)
[Variety] Avoided recent dishes: ['Boiled rice (Uble chawal)', ...]
```

### Future Enhancements

Potential improvements:
- Add user feedback: "Don't recommend this again"
- Season-based variety: Prefer different cuisines by season
- Meal-type awareness: Breakfast dishes for breakfast, dinner dishes for dinner
- Learning from consumption: Track which recommendations were actually eaten
- Cultural preferences: Weight certain cuisines based on regional trends
