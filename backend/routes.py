

from flask import Blueprint, request, jsonify, render_template
from backend.app import db, User   # keep ONLY db & model
import subprocess

routes = Blueprint("routes", __name__)

@routes.route("/test")
def test():
    return "WORKING"

@routes.route("/create-vm", methods=["POST"])
def create_vm():
    try:
        subprocess.run(["terraform", "apply", "-auto-approve"], cwd="../gcp-deploy/infra")
        return {"message": "VM created"}
    except Exception as e:
        return {"error": str(e)}


@routes.route("/register", methods=["POST"])
def register():
    data = request.json
    user = User(email=data["email"], password=data["password"], active=True)
    db.session.add(user)
    db.session.commit()
    return {"message": "User created"}


@routes.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()

    if user and user.password == data["password"]:
        return {"message": "Login successful"}
    return {"message": "Invalid credentials"}


@routes.route("/dashboard")
def dashboard():
    users = User.query.all()
    return {"total_users": len(users)}