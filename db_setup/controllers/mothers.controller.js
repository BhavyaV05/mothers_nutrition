import Mother from "../models/mothers.model.js";
import User from "../models/users.model.js";

// Register a new mother
export const registerMother = async (req, res) => {
  try {
    const { name, phone, expectedDeliveryDate, parity, address } = req.body;

    // Create linked user
    const user = await User.create({
      name,
      phone,
      role: "mother"
    });

    const mother = await Mother.create({
      user: user._id,
      expectedDeliveryDate,
      parity,
      address,
      riskStatus: "normal"
    });

    res.status(201).json({
      motherId: mother._id,
      status: "registered"
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Failed to register mother" });
  }
};
