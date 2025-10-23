import mongoose from "mongoose";

const userSchema = new mongoose.Schema({
  name: { type: String, required: true },
  phone: { type: String, unique: true, required: true },
  passwordHash: { type: String }, // null if OTP based
  role: { type: String, enum: ["mother", "asha", "doctor", "admin"], required: true },
  profile: {
    gender: String,
    dob: Date,
    specialization: String, // doctor
    region: String,         // asha
    language: String
  },
  isActive: { type: Boolean, default: true },
  createdAt: { type: Date, default: Date.now }
});

export default mongoose.model("User", userSchema);
