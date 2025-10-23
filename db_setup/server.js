import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import connectDB from "./config/db.js";
import motherRoutes from "./routes/mothers.routes.js";

dotenv.config();
connectDB(); // Connect to MongoDB first

const app = express(); // <--- app must be created before use()

app.use(cors());
app.use(express.json());

// --- ROUTES ---
app.get("/", (req, res) => res.send("Mother Nutrition Planner API running..."));
app.use("/api/mothers", motherRoutes);

// --- START SERVER ---
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`🚀 Server running on port ${PORT}`));
