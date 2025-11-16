"""
Test script for Query System
Run this after starting the Flask app to test the query endpoints
"""

import requests
import json

BASE_URL = "http://localhost:5000"

# Store session cookies
session = requests.Session()

def test_mother_login():
    """Test mother login"""
    print("\n=== Testing Mother Login ===")
    response = session.post(f"{BASE_URL}/login", data={
        "email": "mother@example.com",  # Replace with actual mother email
        "password": "password123",
        "role": "mother"
    })
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✓ Mother logged in successfully")
    return response.status_code == 200

def test_create_query():
    """Test creating a query"""
    print("\n=== Testing Create Query ===")
    query_data = {
        "subject": "Question about calcium intake",
        "message": "I am lactose intolerant. What are good sources of calcium for pregnant women?",
        "category": "nutrition"
    }
    
    response = session.post(
        f"{BASE_URL}/api/queries/create",
        json=query_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print("✓ Query created successfully")
        print(f"Query ID: {data['query']['_id']}")
        print(f"Subject: {data['query']['subject']}")
        print(f"Status: {data['query']['status']}")
        return data['query']['_id']
    else:
        print(f"✗ Failed: {response.text}")
        return None

def test_get_my_queries():
    """Test getting mother's queries"""
    print("\n=== Testing Get My Queries ===")
    response = session.get(f"{BASE_URL}/api/queries/my-queries")
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Found {data['count']} queries")
        for query in data['queries'][:3]:  # Show first 3
            print(f"  - {query['subject']} [{query['status']}]")
    else:
        print(f"✗ Failed: {response.text}")

def test_get_statistics():
    """Test getting statistics"""
    print("\n=== Testing Get Statistics ===")
    response = session.get(f"{BASE_URL}/api/queries/statistics")
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        stats = data['statistics']
        print(f"✓ Statistics retrieved")
        print(f"  Total queries: {stats['total']}")
        print(f"  By Status: {stats['byStatus']}")
        print(f"  By Category: {stats['byCategory']}")
    else:
        print(f"✗ Failed: {response.text}")

def test_doctor_login():
    """Test doctor login"""
    print("\n=== Testing Doctor Login ===")
    response = session.post(f"{BASE_URL}/login", data={
        "email": "doctor@example.com",  # Replace with actual doctor email
        "password": "password123",
        "role": "doctor"
    })
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✓ Doctor logged in successfully")
    return response.status_code == 200

def test_get_all_queries():
    """Test getting all queries (doctor view)"""
    print("\n=== Testing Get All Queries (Doctor) ===")
    response = session.get(f"{BASE_URL}/api/queries/all?status=pending&limit=5")
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Found {data['count']} pending queries")
        for query in data['queries'][:3]:
            print(f"  - {query['subject']} by {query['motherName']} [{query['category']}]")
        return data['queries'][0]['_id'] if data['queries'] else None
    else:
        print(f"✗ Failed: {response.text}")
        return None

def test_reply_to_query(query_id):
    """Test replying to a query"""
    print("\n=== Testing Reply to Query ===")
    if not query_id:
        print("✗ No query ID provided")
        return
    
    reply_data = {
        "message": "For lactose intolerance, excellent calcium sources include: fortified plant-based milk (almond, soy), tofu, leafy greens (kale, collard greens), almonds, chia seeds, and fortified orange juice. Aim for 1000-1300mg daily during pregnancy.",
        "updateStatus": "resolved"
    }
    
    response = session.post(
        f"{BASE_URL}/api/queries/{query_id}/reply",
        json=reply_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✓ Reply added successfully")
        print(f"New status: {data['query']['status']}")
        print(f"Total replies: {len(data['query']['replies'])}")
    else:
        print(f"✗ Failed: {response.text}")

def test_update_status(query_id):
    """Test updating query status"""
    print("\n=== Testing Update Query Status ===")
    if not query_id:
        print("✗ No query ID provided")
        return
    
    update_data = {
        "status": "closed",
        "priority": "normal"
    }
    
    response = session.put(
        f"{BASE_URL}/api/queries/{query_id}/update-status",
        json=update_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✓ Query status updated")
        print(f"New status: {data['query']['status']}")
    else:
        print(f"✗ Failed: {response.text}")

def run_mother_tests():
    """Run all mother-related tests"""
    print("\n" + "="*50)
    print("MOTHER TESTS")
    print("="*50)
    
    if not test_mother_login():
        print("✗ Mother login failed. Please check credentials.")
        return
    
    query_id = test_create_query()
    test_get_my_queries()
    test_get_statistics()

def run_doctor_tests():
    """Run all doctor-related tests"""
    print("\n" + "="*50)
    print("DOCTOR TESTS")
    print("="*50)
    
    if not test_doctor_login():
        print("✗ Doctor login failed. Please check credentials.")
        return
    
    query_id = test_get_all_queries()
    if query_id:
        test_reply_to_query(query_id)
        # test_update_status(query_id)
    test_get_statistics()

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════╗
    ║   Query System Test Script             ║
    ║   Make sure Flask app is running       ║
    ╚════════════════════════════════════════╝
    """)
    
    choice = input("Test as: (1) Mother, (2) Doctor, (3) Both: ")
    
    if choice == "1":
        run_mother_tests()
    elif choice == "2":
        run_doctor_tests()
    elif choice == "3":
        run_mother_tests()
        run_doctor_tests()
    else:
        print("Invalid choice!")
    
    print("\n" + "="*50)
    print("Tests completed!")
    print("="*50)
