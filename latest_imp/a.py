{% extends "base.html" %}
{% block content %}

<style>
    /* ... (CSS styles remain the same as original) ... */
    /* Only keeping the unique styles for brevity, assuming you have the full CSS */
    .recommendation-card {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        border: 2px solid #667eea30;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.1);
    }
    
    /* ... (Rest of the original CSS styles here) ... */

    .floating-btn {
        /* ... (Floating Button CSS) ... */
        position: fixed;
        right: 24px;
        bottom: 24px;
        width: 64px;
        height: 64px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
        border: none;
        font-size: 28px;
        z-index: 9999;
        cursor: pointer;
        transition: all 0.3s ease;
    }
</style>

<h2 style="color: #667eea; margin-bottom: 1.5rem;">Your Daily Recommendation</h2>

<div id="recommendation-area">
    {% if latest_recommendation %}
        <div class="recommendation-card">
            <p><strong>{{ latest_recommendation.reason }}</strong></p>
            <h3>For your next meal, try: {{ latest_recommendation['Dish Name'] }}</h3>
            <p>We found a recipe for you:</p>
            <a href="{{ latest_recommendation['recipe_link'] }}" target="_blank">
                🍳 View Recipe
            </a>
        </div>
    {% else %}
        <div class="info-card">
            <p>✨ You're doing great! No specific recommendations right now. Keep logging your meals!</p>
        </div>
    {% endif %}
</div>

<div class="row">
    <div class="col-md-6">
        <div class="info-card">
            <h3>👨‍⚕️ Your Assigned Doctor</h3>
            <div id="doctorDetails"><em>Checking assignment...</em></div>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="info-card">
            <h3>🤝 Your ASHA Worker</h3>
            <div id="ashaWorkerDetails"><em>Checking assignment...</em></div>
        </div>
    </div>
</div>

<input type="hidden" id="assignedDoctorId" value="{{ assigned_doctor_id }}" />
<input type="hidden" id="assignedAshaId" value="{{ assigned_asha_id }}" /> 

<div class="card">
    <h2>📸 Upload Meal Photo</h2>
    <p style="color: #718096; margin-bottom: 1.5rem;">Click your meal photo and select the meal type. The date will be recorded automatically.</p>

    <form id="uploadForm">
        <input type="hidden" id="motherId" name="motherId" value="{{ mother_id }}" />
        
        <label for="mealType">Meal Type</label>
        <select id="mealType" name="mealType" required>
            <option value="">-- Select Meal --</option>
            <option value="breakfast">Breakfast</option>
            <option value="lunch">Lunch</option>
            <option value="dinner">Dinner</option>
            <option value="snack">Snack</option>
        </select>
        
        <label for="image">Meal Image (Opens Camera)</label>
        <input 
            id="image" 
            name="image" 
            type="file" 
            accept="image/*" 
            capture="environment" 
            required 
            style="padding: 0.75rem; background: white;"
        /> 
        
        <button type="submit" style="margin-top:1.5rem;">📸 Click & Analyze Meal</button>
    </form>
</div>

<div class="card">
    <h3 style="color: #667eea;">Upload Result</h3>
    <div id="resultArea"><em>No upload yet.</em></div>
</div>

<div class="card">
    <h3 style="color: #667eea;">📋 Your Meal History</h3>
    <button id="refreshHistory">🔄 Refresh History</button>
    <div id="mealHistory"><em>Loading...</em></div>
</div>

<script>
function getMotherId() {
    return document.getElementById("motherId").value.trim();
}

// ... (loadDoctorDetails, loadAshaWorkerDetails, loadMealHistory functions remain the same) ...

async function loadDoctorDetails() {
    const doctorId = document.getElementById("assignedDoctorId").value.trim();
    const detailsDiv = document.getElementById("doctorDetails");
    
    if (!doctorId || doctorId === 'None') {
        detailsDiv.innerHTML = "<em>You have not been assigned a doctor yet.</em>";
        return;
    }
    try {
        const res = await fetch(`/api/doctor/${doctorId}`);
        const doctor = await res.json();
        if (res.ok) {
            detailsDiv.innerHTML = `
                <p style="margin: 0;">
                    <strong style="color: #2c3e50;">Dr. ${doctor.name || 'Name not available'}</strong><br>
                    <span style="color: #718096;">Email: ${doctor.email || 'N/A'}</span>
                </p>
            `;
        } else {
            detailsDiv.innerHTML = `<em>Error: Could not find doctor details.</em>`;
        }
    } catch (err) {
        detailsDiv.innerHTML = `<em>Failed to load doctor information.</em>`;
    }
}

async function loadAshaWorkerDetails() {
    const ashaId = document.getElementById("assignedAshaId").value.trim();
    const detailsDiv = document.getElementById("ashaWorkerDetails");
    
    if (!ashaId || ashaId === 'None') {
        detailsDiv.innerHTML = "<em>You have not been assigned an ASHA worker yet.</em>";
        return;
    }
    try {
        const res = await fetch(`/api/asha/${ashaId}`); 
        const asha = await res.json();
        if (res.ok) {
            detailsDiv.innerHTML = `
                <p style="margin: 0;">
                    <strong style="color: #2c3e50;">${asha.name || 'Name not available'}</strong><br>
                    <span style="color: #718096;">Email: ${asha.email || 'N/A'}</span>
                </p>
            `;
        } else {
            detailsDiv.innerHTML = `<em>Error: Could not find ASHA worker details.</em>`;
        }
    } catch (err) {
        detailsDiv.innerHTML = `<em>Failed to load ASHA worker information.</em>`;
    }
}


async function loadMealHistory() {
    const motherId = getMotherId();
    if (!motherId) return;

    try {
        const res = await fetch(`/api/meals/mother/${motherId}`);
        const meals = await res.json();

        if (!Array.isArray(meals) || meals.length === 0) {
            document.getElementById("mealHistory").innerHTML = "<em>No meals yet.</em>";
            return;
        }

        let html = "";
        meals.forEach((m) => {
            const dish = m.dish_name || "Unknown Dish";
            const mealType = m.mealType ? m.mealType.charAt(0).toUpperCase() + m.mealType.slice(1) : "Meal";
            const mealDate = m.mealDate || "Date Unavailable";

            html += `
                <div class="meal-item">
                    <strong>${dish}</strong>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem;">
                        <span style="color: #4a5568;">${mealType} • ${mealDate}</span>
                        <small style="color: #718096;">Status: ${m.status || "unknown"}</small>
                    </div>
                </div>
            `;
        });
        document.getElementById("mealHistory").innerHTML = html;

    } catch (err) {
        document.getElementById("mealHistory").innerHTML = "<em>Failed to load history.</em>";
    }
}

document.getElementById("refreshHistory").addEventListener("click", () => {
    loadMealHistory();
});

document.getElementById("uploadForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    
    // 💥 REMOVAL: No need to retrieve or set mealDate for FormData, as it's not in the form.
    
    document.getElementById("resultArea").innerHTML = "<div style='color: #667eea;'><strong>⏳ Uploading and Analyzing...</strong><br>Please wait while we process your meal.</div>";

    try {
        // The FormData object 'fd' will correctly include 'motherId', 'mealType', and 'image'
        const res = await fetch("/api/meals/upload", { method: "POST", body: fd });
        const data = await res.json();

        if (!res.ok) {
            document.getElementById("resultArea").innerHTML =
                `<div style='color: #e53e3e;'><strong>❌ Upload Error (${res.status})</strong></div>
                 <pre style="margin-top: 1rem;">` + JSON.stringify(data, null, 2) + "</pre>";
            return;
        }

        document.getElementById("resultArea").innerHTML = `
            <div style="color: #48bb78;">
                <strong>✅ Upload Successful!</strong>
                <p style="margin-top: 0.5rem;">Your meal <strong>${data.meal.dish_name}</strong> has been logged.</p>
            </div>
        `;
        
        const recommendation = data.next_meal_recommendation;
        const recArea = document.getElementById("recommendation-area");
        let recHtml = "";

        if (recommendation) {
            recHtml = `
                <div class="recommendation-card">
                    <p><strong>${recommendation.reason}</strong></p>
                    <h3>For your next meal, try: ${recommendation['Dish Name']}</h3>
                    <p>We found a recipe for you:</p>
                    <a href="${recommendation['recipe_link']}" target="_blank">
                        🍳 View Recipe
                    </a>
                </div>
            `;
        } else {
            recHtml = `
                <div class="info-card">
                    <p>✨ You're doing great! No specific recommendations right now.</p>
                </div>
            `;
        }
        
        recArea.innerHTML = recHtml;
        loadMealHistory();

    } catch (err) {
        document.getElementById("resultArea").innerHTML =
            "<div style='color: #e53e3e;'><strong>❌ Upload failed:</strong> " + err.message + "</div>";
    }
});

window.addEventListener("load", () => {
    loadMealHistory();
    loadDoctorDetails();
    loadAshaWorkerDetails();
});

// ... (Modal/Query functions remain the same) ...

const modal = document.getElementById("queryModal");
const openBtn = document.getElementById("openQueryBtn");
const closeBtn = document.getElementById("closeModal");

openBtn.onclick = function() {
    modal.style.display = "block";
    loadQueryHistory();
}

closeBtn.onclick = function() {
    modal.style.display = "none";
    document.getElementById("querySuccess").style.display = "none";
    document.getElementById("queryForm").reset();
}

window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
        document.getElementById("querySuccess").style.display = "none";
        document.getElementById("queryForm").reset();
    }
}

document.getElementById("queryForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const subject = document.getElementById("querySubject").value;
    const message = document.getElementById("queryMessage").value;

    try {
        const res = await fetch("/api/queries/create", {
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ subject, message, category: "general" })
        });

        const data = await res.json();
        
        if (data.success) {
            document.getElementById("querySuccess").style.display = "block";
            document.getElementById("queryForm").reset();
            loadQueryHistory();
            setTimeout(() => {
                document.getElementById("querySuccess").style.display = "none";
            }, 3000);
        } else {
            alert("Failed to send query: " + (data.error || "Unknown error"));
        }
    } catch (err) {
        alert("Failed to send query. Please try again.");
    }
});

async function loadQueryHistory() {
    try {
        const res = await fetch("/api/queries/my-queries", { credentials: 'include' });
        const data = await res.json();

        if (!data.success || !Array.isArray(data.queries) || data.queries.length === 0) {
            document.getElementById("queryHistoryArea").innerHTML = "<em style='color: #718096;'>No queries yet.</em>";
            return;
        }

        let html = "";
        data.queries.forEach(q => {
            const date = new Date(q.createdAt).toLocaleString();
            
            let statusColor = '#718096';
            if (q.status === 'resolved' || q.status === 'answered') statusColor = '#48bb78';
            else if (q.status === 'in-progress') statusColor = '#667eea';
            else if (q.status === 'pending') statusColor = '#ed8936';
            
            html += `
                <div class="query-history-item">
                    <strong style="color: #667eea; font-size: 1.05em;">${q.subject}</strong>
                    <p style="margin: 0.75rem 0; color: #4a5568;">${q.message}</p>
                    <small style="color: #718096;">
                        ${date} • 
                        <span class="status-badge" style="background: ${statusColor}20; color: ${statusColor};">
                            ${q.status}
                        </span>
                    </small>
            `;
            
            if (q.replies && q.replies.length > 0) {
                html += `<div style="margin-top: 1rem;">`;
                q.replies.forEach(reply => {
                    const replyDate = new Date(reply.repliedAt).toLocaleString();
                    html += `
                        <div class="query-answer">
                            <strong>✓ ${reply.doctorName} replied:</strong>
                            <p style="margin: 0.5rem 0 0 0; color: #2c3e50;">${reply.message}</p>
                            <small style="color: #718096;">${replyDate}</small>
                        </div>
                    `;
                });
                html += `</div>`;
            } else if (q.response) {
                const replyDate = q.respondedAt ? new Date(q.respondedAt).toLocaleString() : 'Date unavailable';
                html += `
                    <div style="margin-top: 1rem;">
                        <div class="query-answer">
                            <strong>✓ Doctor replied:</strong>
                            <p style="margin: 0.5rem 0 0 0; color: #2c3e50;">${q.response}</p>
                            <small style="color: #718096;">${replyDate}</small>
                        </div>
                    </div>
                `;
            } else if (q.status === 'pending') {
                html += `
                    <div style="margin-top: 0.75rem; padding: 0.75rem; background: #fef3c7; border-radius: 8px;">
                        <small style="color: #92400e;">⏳ Waiting for doctor's response...</small>
                    </div>
                `;
            }
            
            html += `</div>`;
        });

        document.getElementById("queryHistoryArea").innerHTML = html;
    } catch (err) {
        document.getElementById("queryHistoryArea").innerHTML = "<em style='color: #e53e3e;'>Failed to load query history.</em>";
    }
}
</script>

{% endblock %}