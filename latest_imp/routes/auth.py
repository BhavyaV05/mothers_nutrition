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

        if role == "mother":
            mother_details = {
                "location": request.form.get("location"),
                "food_pref": request.form.get("food_pref"),
                "area_type": request.form.get("area_type")
            }
        else:
            mother_details = None

        if get_user_by_email(email):
            flash("Email already exists")
            return redirect(url_for("auth.signup"))

        create_user(role, name, email, password, mother_details)
        flash("Signup successful! Login now.")
        return redirect(url_for("auth.login"))

    return render_template("signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = verify_user(email, password)
        if not user:
            flash("Invalid credentials")
            return redirect(url_for("auth.login"))

        session["user_id"] = user["_id"]
        session["role"] = user["role"]

        return redirect(url_for("mother_page" if user["role"] == "mother" else "doctor_page"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
