from datetime import datetime

class Mother:
    def __init__(self, name, phone, expected_delivery_date, parity, address):
        self.name = name
        self.phone = phone
        self.expected_delivery_date = expected_delivery_date
        self.parity = parity
        self.address = address
        self.risk_status = "normal"
        self.created_at = datetime.utcnow()
        
    def to_dict(self):
        return {
            "name": self.name,
            "phone": self.phone,
            "expected_delivery_date": self.expected_delivery_date,
            "parity": self.parity,
            "address": self.address,
            "risk_status": self.risk_status,
            "created_at": self.created_at
        }