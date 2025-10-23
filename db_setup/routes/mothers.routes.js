import express from "express";
import { registerMother } from "../controllers/mothers.controller.js";

const router = express.Router();

router.post("/", registerMother);

export default router;
