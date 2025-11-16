"""
MongoDB Schema Setup and Sample Data for Query System
Run this script to create indexes and insert sample data
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime, timedelta
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.get_default_database()

queries_col = db.get_collection("queries")
users_col = db.get_collection("users")

def create_indexes():
    """Create recommended indexes for better performance"""
    print("Creating indexes...")
    
    # Index for faster queries by mother
    queries_col.create_index([("motherId", ASCENDING), ("createdAt", DESCENDING)])
    
    # Index for filtering by status
    queries_col.create_index([("status", ASCENDING), ("createdAt", DESCENDING)])
    
    # Index for filtering by category and status
    queries_col.create_index([("category", ASCENDING), ("status", ASCENDING)])
    
    # Index for doctor assignments
    queries_col.create_index([("doctorId", ASCENDING), ("createdAt", DESCENDING)])
    
    print("✓ Indexes created successfully!")

def insert_sample_data():
    """Insert sample queries for testing"""
    print("\nInserting sample data...")
    
    # Find a sample mother and doctor from users collection
    sample_mother = users_col.find_one({"role": "mother"})
    sample_doctor = users_col.find_one({"role": "doctor"})
    
    if not sample_mother:
        print("⚠ Warning: No mother found in users collection. Please create a mother user first.")
        return
    
    if not sample_doctor:
        print("⚠ Warning: No doctor found in users collection. Sample replies won't have doctor info.")
    
    # Sample queries
    sample_queries = [
        {
            "motherId": sample_mother["_id"],
            "motherName": sample_mother.get("name", "Sample Mother"),
            "motherEmail": sample_mother.get("email", "mother@example.com"),
            "subject": "Iron deficiency concern",
            "message": "I'm a vegetarian and concerned about iron deficiency during pregnancy. What plant-based foods are rich in iron?",
            "category": "nutrition",
            "status": "pending",
            "priority": "normal",
            "doctorId": None,
            "replies": [],
            "createdAt": datetime.utcnow() - timedelta(hours=2),
            "updatedAt": datetime.utcnow() - timedelta(hours=2)
        },
        {
            "motherId": sample_mother["_id"],
            "motherName": sample_mother.get("name", "Sample Mother"),
            "motherEmail": sample_mother.get("email", "mother@example.com"),
            "subject": "Calcium intake for lactose intolerant",
            "message": "I'm lactose intolerant. How can I meet my calcium requirements during pregnancy?",
            "category": "nutrition",
            "status": "resolved" if sample_doctor else "pending",
            "priority": "high",
            "doctorId": sample_doctor["_id"] if sample_doctor else None,
            "replies": [
                {
                    "doctorId": str(sample_doctor["_id"]) if sample_doctor else "unknown",
                    "doctorName": sample_doctor.get("name", "Dr. Sample") if sample_doctor else "Doctor",
                    "message": "Great question! For lactose intolerance, you can get calcium from: 1) Fortified plant-based milk (almond, soy, oat), 2) Leafy greens like kale and collard greens, 3) Tofu processed with calcium, 4) Almonds and sesame seeds, 5) Fortified orange juice. Aim for 1000-1300mg daily.",
                    "repliedAt": datetime.utcnow() - timedelta(hours=1)
                }
            ] if sample_doctor else [],
            "createdAt": datetime.utcnow() - timedelta(days=1),
            "updatedAt": datetime.utcnow() - timedelta(hours=1) if sample_doctor else datetime.utcnow() - timedelta(days=1)
        },
        {
            "motherId": sample_mother["_id"],
            "motherName": sample_mother.get("name", "Sample Mother"),
            "motherEmail": sample_mother.get("email", "mother@example.com"),
            "subject": "Morning sickness and nutrition",
            "message": "I have severe morning sickness and can't keep most foods down. How can I ensure I'm getting adequate nutrition?",
            "category": "health",
            "status": "in-progress" if sample_doctor else "pending",
            "priority": "urgent",
            "doctorId": sample_doctor["_id"] if sample_doctor else None,
            "replies": [
                {
                    "doctorId": str(sample_doctor["_id"]) if sample_doctor else "unknown",
                    "doctorName": sample_doctor.get("name", "Dr. Sample") if sample_doctor else "Doctor",
                    "message": "I understand this is challenging. Try eating small, frequent meals throughout the day. Bland foods like crackers, toast, and bananas are often tolerated better. Ginger tea can help with nausea. Stay hydrated with small sips of water. I'm consulting with a specialist for personalized advice.",
                    "repliedAt": datetime.utcnow() - timedelta(minutes=30)
                }
            ] if sample_doctor else [],
            "createdAt": datetime.utcnow() - timedelta(hours=3),
            "updatedAt": datetime.utcnow() - timedelta(minutes=30) if sample_doctor else datetime.utcnow() - timedelta(hours=3)
        },
        {
            "motherId": sample_mother["_id"],
            "motherName": sample_mother.get("name", "Sample Mother"),
            "motherEmail": sample_mother.get("email", "mother@example.com"),
            "subject": "Modification to nutrition plan",
            "message": "The current plan has a lot of seafood, but I'm allergic to shellfish. Can we modify it?",
            "category": "plan",
            "status": "pending",
            "priority": "normal",
            "doctorId": None,
            "replies": [],
            "createdAt": datetime.utcnow() - timedelta(hours=5),
            "updatedAt": datetime.utcnow() - timedelta(hours=5)
        },
        {
            "motherId": sample_mother["_id"],
            "motherName": sample_mother.get("name", "Sample Mother"),
            "motherEmail": sample_mother.get("email", "mother@example.com"),
            "subject": "Vitamin D supplementation",
            "message": "Do I need vitamin D supplements during pregnancy? I don't get much sun exposure.",
            "category": "health",
            "status": "closed" if sample_doctor else "pending",
            "priority": "normal",
            "doctorId": sample_doctor["_id"] if sample_doctor else None,
            "replies": [
                {
                    "doctorId": str(sample_doctor["_id"]) if sample_doctor else "unknown",
                    "doctorName": sample_doctor.get("name", "Dr. Sample") if sample_doctor else "Doctor",
                    "message": "Yes, vitamin D is crucial during pregnancy. With limited sun exposure, supplementation is recommended. I'll prescribe 1000-2000 IU daily. Also include vitamin D-rich foods like fortified milk, fatty fish, and egg yolks.",
                    "repliedAt": datetime.utcnow() - timedelta(days=2)
                }
            ] if sample_doctor else [],
            "createdAt": datetime.utcnow() - timedelta(days=3),
            "updatedAt": datetime.utcnow() - timedelta(days=2) if sample_doctor else datetime.utcnow() - timedelta(days=3)
        }
    ]
    
    # Insert queries
    result = queries_col.insert_many(sample_queries)
    print(f"✓ Inserted {len(result.inserted_ids)} sample queries!")
    
    # Display summary
    print("\nSample Data Summary:")
    print(f"  Mother: {sample_mother.get('name', 'Sample Mother')} ({sample_mother.get('email')})")
    if sample_doctor:
        print(f"  Doctor: {sample_doctor.get('name', 'Sample Doctor')} ({sample_doctor.get('email')})")
    print(f"\nQueries by status:")
    for status in ["pending", "in-progress", "resolved", "closed"]:
        count = queries_col.count_documents({"status": status})
        print(f"    {status}: {count}")

def display_schema():
    """Display the schema structure"""
    print("\n" + "="*60)
    print("QUERY COLLECTION SCHEMA")
    print("="*60)
    print("""
{
  _id: ObjectId                    // Unique identifier
  motherId: ObjectId               // Reference to users collection
  motherName: String               // Mother's name (denormalized)
  motherEmail: String              // Mother's email
  subject: String                  // Query title/subject
  message: String                  // Detailed question
  category: String                 // "nutrition", "health", "plan", "general"
  status: String                   // "pending", "in-progress", "resolved", "closed"
  priority: String                 // "low", "normal", "high", "urgent"
  doctorId: ObjectId | null        // Assigned doctor (optional)
  replies: [                       // Array of doctor replies
    {
      doctorId: String,
      doctorName: String,
      message: String,
      repliedAt: DateTime
    }
  ],
  createdAt: DateTime              // When query was created
  updatedAt: DateTime              // Last update time
}
    """)
    print("="*60)

def show_statistics():
    """Show current database statistics"""
    print("\nCurrent Database Statistics:")
    total = queries_col.count_documents({})
    print(f"  Total queries: {total}")
    
    if total > 0:
        print("\n  By Status:")
        for status in ["pending", "in-progress", "resolved", "closed"]:
            count = queries_col.count_documents({"status": status})
            print(f"    {status}: {count}")
        
        print("\n  By Category:")
        for category in ["nutrition", "health", "plan", "general"]:
            count = queries_col.count_documents({"category": category})
            print(f"    {category}: {count}")
        
        print("\n  By Priority:")
        for priority in ["low", "normal", "high", "urgent"]:
            count = queries_col.count_documents({"priority": priority})
            print(f"    {priority}: {count}")

def main():
    """Main setup function"""
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║     Query System - Database Setup & Sample Data        ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    display_schema()
    
    print("\nWhat would you like to do?")
    print("1. Create indexes only")
    print("2. Insert sample data only")
    print("3. Both (recommended for first-time setup)")
    print("4. Show current statistics")
    print("5. Clear all queries (use with caution!)")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == "1":
        create_indexes()
    elif choice == "2":
        insert_sample_data()
    elif choice == "3":
        create_indexes()
        insert_sample_data()
    elif choice == "4":
        show_statistics()
    elif choice == "5":
        confirm = input("Are you sure you want to delete ALL queries? (yes/no): ")
        if confirm.lower() == "yes":
            result = queries_col.delete_many({})
            print(f"✓ Deleted {result.deleted_count} queries")
        else:
            print("Cancelled.")
    else:
        print("Invalid choice!")
        return
    
    show_statistics()
    
    print("\n" + "="*60)
    print("Setup completed successfully!")
    print("="*60)

if __name__ == "__main__":
    main()
