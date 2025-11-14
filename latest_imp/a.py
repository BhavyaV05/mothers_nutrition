@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")
        
        # 1. Retrieve user by email and role
        user = users_col.find_one({"email": email, "role": role})

        # 🔑 SECURITY CHANGE: Check the password against the stored hash 🔑
        # Check if user exists AND the password is correct
        if user and check_password_hash(user.get("password"), password):
            session['user_id'] = str(user['_id'])
            session['role'] = user['role']
            
            return redirect(url_for('index'))
        
        # Authentication failed
        error = "Invalid credentials or role."
        return render_template("login.html", error=error)
        
    return render_template("login.html")