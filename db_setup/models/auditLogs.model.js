import mongoose from "mongoose";

const auditLogSchema = new mongoose.Schema({
  actor: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
  entity: { type: String, required: true },
  action: { type: String, required: true },
  before: mongoose.Schema.Types.Mixed,
  after: mongoose.Schema.Types.Mixed,
  timestamp: { type: Date, default: Date.now }
});

export default mongoose.model("AuditLog", auditLogSchema);
