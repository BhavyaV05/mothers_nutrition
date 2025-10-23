import mongoose from "mongoose";

const alertSchema = new mongoose.Schema({
  mother: { type: mongoose.Schema.Types.ObjectId, ref: "Mother", required: true },
  type: { type: String, enum: ["adherence", "risk", "system"], required: true },
  severity: { type: String, enum: ["low", "medium", "high"], default: "low" },
  message: { type: String, required: true },
  resolved: { type: Boolean, default: false },
  createdAt: { type: Date, default: Date.now },
  resolvedAt: Date
});

export default mongoose.model("Alert", alertSchema);
