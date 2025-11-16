# Query System Implementation Guide

## 📋 Overview

This implementation adds a complete query/messaging system between mothers and doctors in your Mother's Nutrition Tracker application. Mothers can ask questions, and doctors can view and respond to these queries.

## 🗂️ Files Created/Modified

### New Files:
1. **`routes/queries.py`** - Query API endpoints
2. **`test_queries.py`** - Test script for the query system
3. **`QUERY_API_DOCUMENTATION.md`** - Complete API documentation

### Modified Files:
1. **`models.py`** - Added query-related database functions
2. **`app.py`** - Integrated query blueprint

## 📊 Database Schema

A new MongoDB collection `queries` is created with the following structure:

```javascript
{
  _id: ObjectId,
  motherId: ObjectId,           // Reference to users collection
  motherName: String,
  motherEmail: String,
  subject: String,              // Query title
  message: String,              // Query details
  category: String,             // "nutrition", "health", "plan", "general"
  status: String,               // "pending", "in-progress", "resolved", "closed"
  priority: String,             // "low", "normal", "high", "urgent"
  doctorId: ObjectId,           // Assigned doctor (can be null)
  replies: [
    {
      doctorId: String,
      doctorName: String,
      message: String,
      repliedAt: DateTime
    }
  ],
  createdAt: DateTime,
  updatedAt: DateTime
}
```

## 🚀 Setup Instructions

### 1. Install Dependencies (if not already installed)

```bash
cd /home/joharatharv/Desktop/dsi_project/mothers_nutrition/latest_imp
pip install flask pymongo python-dotenv werkzeug
```

### 2. Ensure MongoDB is Running

Make sure your MongoDB instance is accessible and the `MONGO_URI` in your `.env` file is correct.

### 3. Start the Flask Application

```bash
python app.py
```

The app should start on `http://localhost:5000`

## 🧪 Testing the API

### Method 1: Using the Test Script

```bash
python test_queries.py
```

Follow the prompts to test as mother, doctor, or both.

### Method 2: Using cURL

#### Mother Creates a Query:
```bash
# First login as mother and save cookies
curl -X POST http://localhost:5000/login \
  -d "email=mother@example.com&password=yourpassword&role=mother" \
  -c cookies.txt

# Create a query
curl -X POST http://localhost:5000/api/queries/create \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "subject": "Iron deficiency concern",
    "message": "What are good iron sources for vegetarians?",
    "category": "nutrition"
  }'
```

#### Mother Views Her Queries:
```bash
curl http://localhost:5000/api/queries/my-queries \
  -b cookies.txt
```

#### Doctor Views All Queries:
```bash
# Login as doctor
curl -X POST http://localhost:5000/login \
  -d "email=doctor@example.com&password=yourpassword&role=doctor" \
  -c cookies_doctor.txt

# Get all pending queries
curl http://localhost:5000/api/queries/all?status=pending \
  -b cookies_doctor.txt
```

#### Doctor Replies to a Query:
```bash
curl -X POST http://localhost:5000/api/queries/QUERY_ID_HERE/reply \
  -H "Content-Type: application/json" \
  -b cookies_doctor.txt \
  -d '{
    "message": "Include spinach, lentils, tofu, and fortified cereals in your diet.",
    "updateStatus": "resolved"
  }'
```

### Method 3: Using Postman

1. Import the endpoints from `QUERY_API_DOCUMENTATION.md`
2. Set up session cookies by logging in first
3. Test each endpoint with sample data

## 📱 Frontend Integration

### For Mother Page (`mother.html`)

Add a query section to your template:

```html
<!-- Query Section -->
<div class="query-section">
  <h2>Ask a Question</h2>
  <form id="queryForm">
    <input type="text" id="subject" placeholder="Subject" required>
    <textarea id="message" placeholder="Your question..." required></textarea>
    <select id="category">
      <option value="nutrition">Nutrition</option>
      <option value="health">Health</option>
      <option value="plan">Nutrition Plan</option>
      <option value="general">General</option>
    </select>
    <button type="submit">Submit Query</button>
  </form>
  
  <h3>My Queries</h3>
  <div id="queriesList"></div>
</div>

<script>
// Submit query
document.getElementById('queryForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const response = await fetch('/api/queries/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      subject: document.getElementById('subject').value,
      message: document.getElementById('message').value,
      category: document.getElementById('category').value
    })
  });
  
  const data = await response.json();
  if (data.success) {
    alert('Query submitted successfully!');
    loadMyQueries();
    e.target.reset();
  }
});

// Load mother's queries
async function loadMyQueries() {
  const response = await fetch('/api/queries/my-queries');
  const data = await response.json();
  
  const list = document.getElementById('queriesList');
  list.innerHTML = data.queries.map(q => `
    <div class="query-card ${q.status}">
      <h4>${q.subject}</h4>
      <p>${q.message}</p>
      <span class="status">${q.status}</span>
      <span class="category">${q.category}</span>
      ${q.replies.map(r => `
        <div class="reply">
          <strong>${r.doctorName}:</strong> ${r.message}
          <small>${new Date(r.repliedAt).toLocaleString()}</small>
        </div>
      `).join('')}
    </div>
  `).join('');
}

// Load queries on page load
loadMyQueries();
</script>
```

### For Doctor Page (`doctor.html`)

```html
<!-- Queries Section -->
<div class="queries-section">
  <h2>Patient Queries</h2>
  
  <div class="filters">
    <select id="statusFilter" onchange="loadQueries()">
      <option value="">All Status</option>
      <option value="pending">Pending</option>
      <option value="in-progress">In Progress</option>
      <option value="resolved">Resolved</option>
    </select>
    
    <select id="categoryFilter" onchange="loadQueries()">
      <option value="">All Categories</option>
      <option value="nutrition">Nutrition</option>
      <option value="health">Health</option>
      <option value="plan">Plan</option>
    </select>
  </div>
  
  <div id="queriesList"></div>
</div>

<script>
// Load all queries
async function loadQueries() {
  const status = document.getElementById('statusFilter').value;
  const category = document.getElementById('categoryFilter').value;
  
  let url = '/api/queries/all?';
  if (status) url += `status=${status}&`;
  if (category) url += `category=${category}&`;
  
  const response = await fetch(url);
  const data = await response.json();
  
  const list = document.getElementById('queriesList');
  list.innerHTML = data.queries.map(q => `
    <div class="query-card">
      <h4>${q.subject}</h4>
      <p><strong>From:</strong> ${q.motherName} (${q.motherEmail})</p>
      <p>${q.message}</p>
      <span class="badge ${q.status}">${q.status}</span>
      <span class="badge ${q.category}">${q.category}</span>
      
      <div class="replies">
        ${q.replies.map(r => `
          <div class="reply">
            <strong>${r.doctorName}:</strong> ${r.message}
          </div>
        `).join('')}
      </div>
      
      <div class="reply-form">
        <textarea id="reply-${q._id}" placeholder="Your reply..."></textarea>
        <button onclick="replyToQuery('${q._id}')">Send Reply</button>
      </div>
    </div>
  `).join('');
}

// Reply to query
async function replyToQuery(queryId) {
  const message = document.getElementById(`reply-${queryId}`).value;
  
  if (!message.trim()) {
    alert('Please enter a reply');
    return;
  }
  
  const response = await fetch(`/api/queries/${queryId}/reply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: message,
      updateStatus: 'resolved'  // or let doctor choose
    })
  });
  
  const data = await response.json();
  if (data.success) {
    alert('Reply sent successfully!');
    loadQueries();
  }
}

// Load queries on page load
loadQueries();
</script>
```

## 🎨 CSS Styling (Optional)

Add to your `static/style.css` or inline styles:

```css
.query-card {
  border: 1px solid #ddd;
  padding: 15px;
  margin: 10px 0;
  border-radius: 8px;
  background: white;
}

.query-card.pending { border-left: 4px solid #ff9800; }
.query-card.in-progress { border-left: 4px solid #2196F3; }
.query-card.resolved { border-left: 4px solid #4CAF50; }
.query-card.closed { border-left: 4px solid #9E9E9E; }

.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  margin: 5px;
}

.badge.pending { background: #ff9800; color: white; }
.badge.in-progress { background: #2196F3; color: white; }
.badge.resolved { background: #4CAF50; color: white; }

.reply {
  background: #f5f5f5;
  padding: 10px;
  margin: 10px 0;
  border-radius: 4px;
}

.reply-form textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin: 10px 0;
}
```

## 📊 API Endpoints Summary

### Mother Endpoints:
- `POST /api/queries/create` - Create new query
- `GET /api/queries/my-queries` - View own queries
- `GET /api/queries/{id}` - View specific query

### Doctor Endpoints:
- `GET /api/queries/all` - View all queries
- `POST /api/queries/{id}/reply` - Reply to query
- `PUT /api/queries/{id}/update-status` - Update status
- `PUT /api/queries/{id}/assign` - Assign to doctor

### Common:
- `GET /api/queries/statistics` - Get statistics

## 🔍 Troubleshooting

### Issue: "Import errors" in VS Code
**Solution:** These are false positives if dependencies aren't installed in the VS Code Python environment. The code will work when run.

### Issue: Authentication errors
**Solution:** Make sure you're logged in before accessing endpoints. Use session cookies.

### Issue: Empty queries list
**Solution:** Create some test queries first using the mother account.

### Issue: MongoDB connection error
**Solution:** Check your `.env` file has correct `MONGO_URI`

## 📈 Next Steps

1. **Add to templates**: Integrate the HTML/JavaScript code into your existing `mother.html` and `doctor.html` templates
2. **Style it**: Add CSS to match your app's design
3. **Test thoroughly**: Use the test script to verify all functionality
4. **Add notifications**: Consider adding email/SMS notifications when queries are answered
5. **Implement search**: Add search functionality for doctors to find specific queries

## 📝 Notes

- All queries are automatically assigned "pending" status when created
- Status automatically changes to "in-progress" when doctor first replies
- Doctors can manually update status to "resolved" or "closed"
- Priority can be set by doctors to organize urgent queries
- All timestamps are in UTC format

## 🤝 Support

For issues or questions:
1. Check the `QUERY_API_DOCUMENTATION.md` for detailed API specs
2. Run `test_queries.py` to verify functionality
3. Check Flask console logs for errors

---

**Implementation completed successfully! ✅**

Your backend for the query system is now ready. Your teammate can integrate the frontend using the provided examples and API documentation.
