import mongoose from "mongoose";

const notificationSchema = new mongoose.Schema({
  channel: { type: String, enum: ["sms", "push"], required: true },
  to: { type: String, required: true },
  templateId: { type: String },
  data: mongoose.Schema.Types.Mixed,
  status: { type: String, enum: ["pending", "sent", "failed"], default: "pending" },
  messageId: String,
  createdAt: { type: Date, default: Date.now }
});

export default mongoose.model("Notification", notificationSchema);
