import mongoose from "mongoose";

const mealSchema = new mongoose.Schema({
  mother: { type: mongoose.Schema.Types.ObjectId, ref: "Mother", required: true },
  mealType: { type: String, enum: ["breakfast", "lunch", "dinner", "snack"], required: true },
  mealDate: { type: Date, required: true },
  imageUrl: { type: String, required: true },
  nutrients: {
    kcal: Number,
    protein_g: Number,
    carb_g: Number,
    fat_g: Number
  },
  labels: {
    tags: [String],
    confidence: Number
  },
  status: { type: String, enum: ["pending", "processed"], default: "pending" },
  createdAt: { type: Date, default: Date.now }
});

export default mongoose.model("Meal", mealSchema);
