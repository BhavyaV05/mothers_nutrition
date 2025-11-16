# Query System API Documentation

## Overview
The Query System enables mothers to ask questions and receive responses from doctors. All queries are stored in MongoDB in the `queries` collection.

---

## Database Schema

### Queries Collection

```json
{
  "_id": "ObjectId",
  "motherId": "ObjectId (reference to users collection)",
  "motherName": "string",
  "motherEmail": "string",
  "subject": "string",
  "message": "string",
  "category": "nutrition | health | plan | general",
  "status": "pending | in-progress | resolved | closed",
  "priority": "low | normal | high | urgent",
  "doctorId": "ObjectId (reference to users collection) | null",
  "replies": [
    {
      "doctorId": "string",
      "doctorName": "string",
      "message": "string",
      "repliedAt": "datetime"
    }
  ],
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

---

## API Endpoints

### 1. Mother Endpoints

#### **POST /api/queries/create**
Create a new query (Mother only)

**Authentication Required:** Yes (Mother role)

**Request Body:**
```json
{
  "subject": "Question about iron intake",
  "message": "I'm concerned about my iron levels. What foods should I eat?",
  "category": "nutrition"
}
```

**Fields:**
- `subject` (required): Brief title of the query
- `message` (required): Detailed question or concern
- `category` (optional): One of ["nutrition", "health", "plan", "general"] (default: "general")

**Response (201):**
```json
{
  "success": true,
  "message": "Query created successfully",
  "query": {
    "_id": "673d5e9a1234567890abcdef",
    "motherId": "673d5e9a1234567890abcd00",
    "motherName": "Priya Sharma",
    "motherEmail": "priya@example.com",
    "subject": "Question about iron intake",
    "message": "I'm concerned about my iron levels. What foods should I eat?",
    "category": "nutrition",
    "status": "pending",
    "priority": "normal",
    "doctorId": null,
    "replies": [],
    "createdAt": "2024-11-16T10:30:00.000Z",
    "updatedAt": "2024-11-16T10:30:00.000Z"
  }
}
```

**Error Responses:**
- `400`: Missing subject or message
- `403`: Not authorized (non-mother trying to create query)

---

#### **GET /api/queries/my-queries**
Get all queries created by the logged-in mother

**Authentication Required:** Yes (Mother role)

**Query Parameters:**
- `status` (optional): Filter by status (pending, in-progress, resolved, closed)
- `limit` (optional): Number of results to return (default: 50)

**Example Request:**
```
GET /api/queries/my-queries?status=pending&limit=20
```

**Response (200):**
```json
{
  "success": true,
  "count": 5,
  "queries": [
    {
      "_id": "673d5e9a1234567890abcdef",
      "motherId": "673d5e9a1234567890abcd00",
      "motherName": "Priya Sharma",
      "subject": "Question about iron intake",
      "message": "I'm concerned about my iron levels...",
      "category": "nutrition",
      "status": "in-progress",
      "priority": "normal",
      "doctorId": "673d5e9a1234567890abcd11",
      "replies": [
        {
          "doctorId": "673d5e9a1234567890abcd11",
          "doctorName": "Dr. Amit Patel",
          "message": "Include spinach, lentils, and fortified cereals in your diet...",
          "repliedAt": "2024-11-16T11:00:00.000Z"
        }
      ],
      "createdAt": "2024-11-16T10:30:00.000Z",
      "updatedAt": "2024-11-16T11:00:00.000Z"
    }
    // ... more queries
  ]
}
```

---

#### **GET /api/queries/{query_id}**
Get details of a specific query

**Authentication Required:** Yes (Mother who created it, or any Doctor)

**Response (200):**
```json
{
  "success": true,
  "query": {
    // Full query object with all details
  }
}
```

**Error Responses:**
- `400`: Invalid query ID
- `403`: Mother trying to view another mother's query
- `404`: Query not found

---

### 2. Doctor Endpoints

#### **GET /api/queries/all**
Get all queries (Doctor only)

**Authentication Required:** Yes (Doctor role)

**Query Parameters:**
- `status` (optional): Filter by status
- `category` (optional): Filter by category
- `priority` (optional): Filter by priority
- `limit` (optional): Number of results (default: 100)

**Example Request:**
```
GET /api/queries/all?status=pending&category=nutrition&limit=50
```

**Response (200):**
```json
{
  "success": true,
  "count": 15,
  "queries": [
    // Array of query objects
  ]
}
```

---

#### **POST /api/queries/{query_id}/reply**
Reply to a query (Doctor only)

**Authentication Required:** Yes (Doctor role)

**Request Body:**
```json
{
  "message": "Include spinach, lentils, dates, and fortified cereals. Consume with vitamin C-rich foods for better absorption.",
  "updateStatus": "in-progress"
}
```

**Fields:**
- `message` (required): The doctor's reply
- `updateStatus` (optional): New status (in-progress, resolved, closed)

**Response (200):**
```json
{
  "success": true,
  "message": "Reply added successfully",
  "query": {
    // Updated query object with the new reply
  }
}
```

**Error Responses:**
- `400`: Missing message or invalid query ID
- `403`: Non-doctor trying to reply
- `404`: Query not found

---

#### **PUT /api/queries/{query_id}/update-status**
Update query status or priority (Doctor only)

**Authentication Required:** Yes (Doctor role)

**Request Body:**
```json
{
  "status": "resolved",
  "priority": "normal"
}
```

**Fields:**
- `status` (optional): New status (pending, in-progress, resolved, closed)
- `priority` (optional): New priority (low, normal, high, urgent)

**Response (200):**
```json
{
  "success": true,
  "message": "Query updated successfully",
  "query": {
    // Updated query object
  }
}
```

---

#### **PUT /api/queries/{query_id}/assign**
Assign query to a specific doctor

**Authentication Required:** Yes (Doctor role)

**Request Body:**
```json
{
  "doctorId": "673d5e9a1234567890abcd11"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Query assigned successfully",
  "query": {
    // Updated query object
  }
}
```

---

### 3. Common Endpoints

#### **GET /api/queries/statistics**
Get query statistics

**Authentication Required:** Yes (Mother or Doctor)

- **For mothers:** Returns statistics for their own queries
- **For doctors:** Returns overall system statistics

**Response (200):**
```json
{
  "success": true,
  "statistics": {
    "total": 45,
    "byStatus": {
      "pending": 12,
      "in-progress": 15,
      "resolved": 15,
      "closed": 3
    },
    "byCategory": {
      "nutrition": 20,
      "health": 15,
      "plan": 7,
      "general": 3
    }
  }
}
```

---

## Usage Examples

### Mother Creating a Query

```javascript
// Frontend JavaScript example
fetch('/api/queries/create', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    subject: "Concerned about calcium intake",
    message: "I'm lactose intolerant. What are good calcium sources?",
    category: "nutrition"
  })
})
.then(response => response.json())
.then(data => {
  console.log('Query created:', data.query);
});
```

### Mother Viewing Her Queries

```javascript
fetch('/api/queries/my-queries?status=pending')
  .then(response => response.json())
  .then(data => {
    console.log(`Found ${data.count} pending queries`);
    data.queries.forEach(query => {
      console.log(`${query.subject} - Status: ${query.status}`);
    });
  });
```

### Doctor Viewing All Queries

```javascript
fetch('/api/queries/all?category=nutrition&status=pending')
  .then(response => response.json())
  .then(data => {
    console.log(`${data.count} pending nutrition queries`);
  });
```

### Doctor Replying to a Query

```javascript
const queryId = '673d5e9a1234567890abcdef';

fetch(`/api/queries/${queryId}/reply`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: "Try calcium-fortified plant milk, tofu, almonds, and leafy greens like kale and broccoli.",
    updateStatus: "resolved"
  })
})
.then(response => response.json())
.then(data => {
  console.log('Reply added:', data.query);
});
```

---

## Status Flow

```
pending → in-progress → resolved → closed
```

- **pending**: Query just created, awaiting doctor response
- **in-progress**: Doctor is working on it (automatically set on first reply)
- **resolved**: Doctor has provided a solution
- **closed**: Query is archived/no longer active

---

## Priority Levels

- **low**: Non-urgent general questions
- **normal**: Standard queries (default)
- **high**: Important health concerns
- **urgent**: Critical/immediate attention needed

---

## Categories

- **nutrition**: Diet, meal planning, nutrient intake
- **health**: Medical conditions, symptoms, wellness
- **plan**: Nutrition plan questions, modifications
- **general**: Other questions

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200`: Success
- `201`: Resource created
- `400`: Bad request (validation error)
- `401`: Authentication required
- `403`: Forbidden (insufficient permissions)
- `404`: Resource not found
- `500`: Server error

Error response format:
```json
{
  "error": "Description of the error"
}
```

---

## Testing with cURL

### Create a Query (Mother)
```bash
curl -X POST http://localhost:5000/api/queries/create \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "subject": "Iron deficiency",
    "message": "What foods are rich in iron?",
    "category": "nutrition"
  }'
```

### Get All Queries (Doctor)
```bash
curl http://localhost:5000/api/queries/all?status=pending \
  -b cookies.txt
```

### Reply to Query (Doctor)
```bash
curl -X POST http://localhost:5000/api/queries/673d5e9a1234567890abcdef/reply \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "message": "Include spinach, lentils, and red meat in your diet.",
    "updateStatus": "resolved"
  }'
```

---

## Integration Notes

1. **Authentication**: All endpoints require session-based authentication
2. **Role-based Access**: Mothers can only create and view their own queries; Doctors can view and respond to all queries
3. **Real-time Updates**: Consider implementing WebSockets for real-time notifications
4. **Pagination**: For large datasets, implement pagination in frontend
5. **Search**: Consider adding search functionality for filtering queries by keywords

---

## Database Indexes (Recommended)

For optimal performance, create these indexes in MongoDB:

```javascript
db.queries.createIndex({ "motherId": 1, "createdAt": -1 });
db.queries.createIndex({ "status": 1, "createdAt": -1 });
db.queries.createIndex({ "category": 1, "status": 1 });
db.queries.createIndex({ "doctorId": 1, "createdAt": -1 });
```

---

## Future Enhancements

1. Attachment support (images, documents)
2. Email notifications for new replies
3. Query templates for common questions
4. Bulk reply/update operations
5. Query forwarding to specialists
6. Rating/feedback system for doctor responses
