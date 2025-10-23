import mongoose from "mongoose";

const motherSchema = new mongoose.Schema({
  user: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
  expectedDeliveryDate: { type: Date, required: true },
  parity: { type: Number, default: 0 },
  address: { type: String },
  asha: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
  doctor: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
  riskStatus: { type: String, enum: ["normal", "warning", "critical"], default: "normal" },
  status: { type: String, enum: ["registered", "archived"], default: "registered" },
  createdAt: { type: Date, default: Date.now }
});

export default mongoose.model("Mother", motherSchema);
