from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import create_user, verify_user, get_user_by_email

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        role = request.form.get("role")
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        # Mother-specific fields
        if role == "mother":
            mother_details = {
                "location": request.form.get("location"),
                "food_pref": request.form.get("food_pref"),
                "area_type": request.form.get("area_type")
            }
        else:
            mother_details = None

        # ASHA-specific fields
        if role == "asha":
            asha_details = {
                "asha_worker_id": request.form.get("asha_worker_id"),
                "phone": request.form.get("phone"),
                "assigned_area": request.form.get("assigned_area")
            }
        else:
            asha_details = None

        if get_user_by_email(email):
            flash("Email already exists")
            return redirect(url_for("auth.signup"))

        # UPDATED: pass ASHA details also
        create_user(role, name, email, password, mother_details, asha_details)

        flash("Signup successful! Login now.")
        return redirect(url_for("auth.login"))

    return render_template("signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")  # <-- ADDED, needed to match

        user = get_user_by_email(email)

        if not user:
            flash("User not found")
            return redirect(url_for("auth.login"))

        # verify password only
        if not verify_user(email, password):
            flash("Invalid password")
            return redirect(url_for("auth.login"))

        # Also check selected role matches stored role
        if user["role"] != role:
            flash("Incorrect role selected")
            return redirect(url_for("auth.login"))

        session["user_id"] = str(user["_id"])
        session["role"] = user["role"]

        # UPDATED REDIRECT LOGIC FOR 3 ROLES
        if user["role"] == "mother":
            return redirect(url_for("mother_page"))
        elif user["role"] == "doctor":
            return redirect(url_for("doctor_page"))
        elif user["role"] == "asha":
            return redirect(url_for("asha_page"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
