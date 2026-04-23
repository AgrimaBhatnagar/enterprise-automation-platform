from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore
import uuid
import subprocess
import os
from datetime import datetime

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "../templates")
)

app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'

db = SQLAlchemy(app)

# ================= MODELS =================

roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean)

    fs_uniquifier = db.Column(
        db.String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )

    roles = db.relationship('Role', secondary=roles_users)

class VMRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(255))
    status = db.Column(db.String(50))

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255))
    user_email = db.Column(db.String(255))
    status = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ================= SETUP =================

datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, datastore)

with app.app_context():
    db.create_all()

    if not datastore.find_role('admin'):
        datastore.create_role(name='admin')
    if not datastore.find_role('user'):
        datastore.create_role(name='user')

    db.session.commit()

    if not datastore.find_user(email="admin@gmail.com"):
        datastore.create_user(
            email="admin@gmail.com",
            password="admin",
            active=True,
            roles=["admin"]
        )
    db.session.commit()

# ================= ROUTES =================

@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    user = User(email=data["email"], password=data["password"], active=True)
    db.session.add(user)
    db.session.commit()
    return {"message": "User created"}

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()

    if user and user.password == data["password"]:
        return {"message": "Login successful"}
    return {"message": "Invalid credentials"}

# ================= WORKFLOW =================

@app.route("/request-vm", methods=["POST"])
def request_vm():
    data = request.json

    req = VMRequest(user_email=data["email"], status="pending")
    db.session.add(req)

    log = Log(
        action="VM Request Created",
        user_email=data["email"],
        status="pending"
    )
    db.session.add(log)

    db.session.commit()

    return {"message": "Request submitted"}

@app.route("/approve-vm/<int:req_id>", methods=["POST"])
def approve_vm(req_id):
    req = VMRequest.query.get(req_id)

    if not req:
        return {"error": "Request not found"}

    req.status = "approved"

    db.session.add(Log(
        action="VM Approved",
        user_email=req.user_email,
        status="approved"
    ))

    db.session.commit()

    try:
        # Terraform
        subprocess.run(
            ["terraform", "apply", "-auto-approve"],
            cwd="../gcp-deploy/infra",
            check=True
        )

        # Get IP
        result = subprocess.check_output(
            ["terraform", "output", "-raw", "vm_ip"],
            cwd="../gcp-deploy/infra"
        )
        ip = result.decode().strip()

        # Ansible
        subprocess.run(
            ["ansible-playbook", "-i", f"{ip},", "../gcp-deploy/ansible/setup.yml"],
            check=True
        )

        req.status = "completed"

        db.session.add(Log(
            action="VM Created",
            user_email=req.user_email,
            status="completed"
        ))

        db.session.commit()

        return {"message": f"VM ready at {ip}"}

    except Exception as e:
        req.status = "failed"

        db.session.add(Log(
            action="ERROR",
            user_email=req.user_email,
            status=str(e)
        ))

        db.session.commit()

        return {"error": str(e)}

# ================= DATA =================

@app.route("/dashboard")
def dashboard():
    requests = VMRequest.query.all()

    return {
        "requests": [
            {"id": r.id, "user": r.user_email, "status": r.status}
            for r in requests
        ]
    }

@app.route("/logs")
def logs():
    logs = Log.query.all()

    return {
        "logs": [
            {
                "action": l.action,
                "user": l.user_email,
                "status": l.status,
                "time": str(l.timestamp)
            }
            for l in logs
        ]
    }

# ================= RUN =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)