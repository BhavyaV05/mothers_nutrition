import mongoose from "mongoose";

const messageSchema = new mongoose.Schema({
  thread: { type: mongoose.Schema.Types.ObjectId, ref: "Query", required: true },
  sender: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
  body: { type: String, required: true },
  attachments: [{
    type: { type: String, enum: ["image", "file", "audio"] },
    url: String
  }],
  timestamp: { type: Date, default: Date.now }
});

export default mongoose.model("Message", messageSchema);
