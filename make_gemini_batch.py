import pandas as pd
import math
import os

# Path to your CSV
CSV_PATH = "./data/Indian_Food_Nutrition_Processed.csv"

# Column name containing dishes
DISH_COL = "Dish Name"

# Number of dishes per batch
BATCH_SIZE = 100

# Output file
OUTPUT_FILE = "./data/gemini_batches.txt"
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# Read file
df = pd.read_csv(CSV_PATH)
df.columns = df.columns.str.strip()  # Clean headers
dishes = df[DISH_COL].dropna().tolist()

total = len(dishes)
num_batches = math.ceil(total / BATCH_SIZE)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(f"Total dishes: {total}\n")
    f.write(f"Generating {num_batches} batches of {BATCH_SIZE} each.\n\n")

    for i in range(num_batches):
        start = i * BATCH_SIZE
        end = min((i + 1) * BATCH_SIZE, total)
        batch = dishes[start:end]

        f.write(f"========== 🍽️  BATCH {i+1} ({start+1}–{end}) ==========\n\n")

        for idx, dish in enumerate(batch, start=start+1):
            f.write(f"{idx}. {dish}\n")

        f.write("\n--------------------------------------------\n\n")

print(f"✅ Batches written to {OUTPUT_FILE}")
