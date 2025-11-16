# Query System - Quick Reference Card

## 🚀 Quick Start

```bash
# 1. Start your Flask app
python app.py

# 2. Setup database (optional - creates indexes and sample data)
python setup_query_db.py

# 3. Test the API
python test_queries.py
```

## 📌 Key Endpoints

### Mother Actions
| Action | Method | Endpoint | Auth |
|--------|--------|----------|------|
| Create query | POST | `/api/queries/create` | Mother |
| View my queries | GET | `/api/queries/my-queries` | Mother |
| View query details | GET | `/api/queries/{id}` | Mother/Doctor |
| Get statistics | GET | `/api/queries/statistics` | Mother/Doctor |

### Doctor Actions
| Action | Method | Endpoint | Auth |
|--------|--------|----------|------|
| View all queries | GET | `/api/queries/all` | Doctor |
| Reply to query | POST | `/api/queries/{id}/reply` | Doctor |
| Update status | PUT | `/api/queries/{id}/update-status` | Doctor |
| Assign to doctor | PUT | `/api/queries/{id}/assign` | Doctor |

## 📊 Query Status Flow

```
pending → in-progress → resolved → closed
```

## 🏷️ Categories
- `nutrition` - Diet and meal questions
- `health` - Medical/wellness concerns  
- `plan` - Nutrition plan modifications
- `general` - Other questions

## ⚡ Priority Levels
- `low` - Non-urgent
- `normal` - Standard (default)
- `high` - Important
- `urgent` - Needs immediate attention

## 💡 Common Examples

### Mother Creates Query
```javascript
fetch('/api/queries/create', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    subject: "Iron deficiency",
    message: "What foods are rich in iron?",
    category: "nutrition"
  })
});
```

### Doctor Replies
```javascript
fetch('/api/queries/QUERY_ID/reply', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    message: "Include spinach, lentils, and dates...",
    updateStatus: "resolved"
  })
});
```

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | False positive - dependencies installed |
| Auth errors | Login first, use session cookies |
| Empty list | Create test queries first |
| Connection error | Check MONGO_URI in .env |

## 📁 File Structure

```
latest_imp/
├── routes/
│   └── queries.py          # Query endpoints
├── models.py               # +Query functions
├── app.py                  # +Blueprint registration
├── test_queries.py         # Test script
├── setup_query_db.py       # DB setup & samples
├── QUERY_API_DOCUMENTATION.md
└── IMPLEMENTATION_GUIDE.md
```

## 📝 Database Collection

**Collection Name:** `queries`

**Key Fields:**
- `motherId` - Who asked
- `subject` - Query title
- `message` - Question details
- `status` - Current state
- `replies[]` - Doctor responses
- `category` - Topic area
- `priority` - Urgency level

## 🎯 Next Steps for Your Teammate (Frontend)

1. Add query form to `mother.html`
2. Add query list display to `mother.html`  
3. Add query management to `doctor.html`
4. Style with CSS
5. Add real-time updates (optional)

## 📞 Integration Points

```javascript
// Mother page needs:
- Form to create query
- List to display queries
- View for replies

// Doctor page needs:
- Filter for queries (status, category)
- Reply interface
- Status update controls
```

## 🔐 Security Notes

- All endpoints require authentication
- Mothers can only see their queries
- Doctors can see all queries
- Session-based auth (cookies)

## ✅ Checklist

- [ ] Flask app running
- [ ] MongoDB connected
- [ ] Indexes created (optional)
- [ ] Test data inserted (optional)
- [ ] API tested with test script
- [ ] Frontend integration started
- [ ] Styling applied

---

**Ready to use! Your backend is complete. 🎉**

See `IMPLEMENTATION_GUIDE.md` for detailed instructions.
See `QUERY_API_DOCUMENTATION.md` for full API specs.
