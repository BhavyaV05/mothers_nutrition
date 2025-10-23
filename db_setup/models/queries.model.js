import mongoose from "mongoose";

const querySchema = new mongoose.Schema({
  mother: { type: mongoose.Schema.Types.ObjectId, ref: "Mother", required: true },
  doctor: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
  topic: { type: String, enum: ["nutrition", "symptom", "other"], default: "other" },
  status: { type: String, enum: ["open", "closed"], default: "open" },
  createdAt: { type: Date, default: Date.now }
});

export default mongoose.model("Query", querySchema);
