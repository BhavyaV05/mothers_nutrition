import mongoose from "mongoose";

const itemSchema = new mongoose.Schema({
  time: String,
  name: String,
  kcal: Number,
  notes: String
}, { _id: false });

const daySchema = new mongoose.Schema({
  day: String,
  items: [itemSchema]
}, { _id: false });

const weekSchema = new mongoose.Schema({
  week: Number,
  days: [daySchema]
}, { _id: false });

const planSchema = new mongoose.Schema({
  mother: { type: mongoose.Schema.Types.ObjectId, ref: "Mother", required: true },
  title: { type: String, required: true },
  status: { type: String, enum: ["active", "archived"], default: "active" },
  weeks: [weekSchema],
  createdBy: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
  createdAt: { type: Date, default: Date.now }
});

export default mongoose.model("NutritionPlan", planSchema);
