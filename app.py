from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os

app = Flask(__name__)
CORS(app)

# ================= CONFIG =================
DATABASE_URL = os.environ.get('DATABASE_URL')

# Railway fix for postgres URL
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///database.db'
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'secret123')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
jwt = JWTManager(app)

# ================= MODELS =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20), default="Member")

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    created_by = db.Column(db.Integer)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    project_id = db.Column(db.Integer)
    assigned_to = db.Column(db.Integer)
    status = db.Column(db.String(20), default="Pending")

# ================= FRONTEND =================
@app.route("/")
def home():
    return send_file("index.html")

# ================= DB INIT =================
@app.route("/init-db")
def init_db():
    db.create_all()
    return {"message": "Tables created"}

# ================= AUTH =================
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "Member")

    if not name or not email or not password:
        return {"error": "Missing fields"}, 400

    if User.query.filter_by(email=email).first():
        return {"error": "User exists"}, 400

    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        role=role
    )

    db.session.add(user)
    db.session.commit()

    return {"message": "User created"}

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    user = User.query.filter_by(email=data["email"]).first()

    if not user or not check_password_hash(user.password, data["password"]):
        return {"error": "Invalid credentials"}, 401

    token = create_access_token(identity=str(user.id))

    return {"token": token, "role": user.role}

# ================= PROJECT =================
@app.route("/projects", methods=["POST"])
@jwt_required()
def create_project():
    user_id = get_jwt_identity()
    data = request.get_json()

    project = Project(name=data["name"], created_by=user_id)

    db.session.add(project)
    db.session.commit()

    return {"message": "Project created"}

@app.route("/projects", methods=["GET"])
@jwt_required()
def get_projects():
    projects = Project.query.all()

    return [{"id": p.id, "name": p.name} for p in projects]

# ================= TASK =================
@app.route("/tasks", methods=["POST"])
@jwt_required()
def create_task():
    data = request.get_json()

    task = Task(
        title=data["title"],
        project_id=data["project_id"],
        assigned_to=data["assigned_to"],
        status="Pending"
    )

    db.session.add(task)
    db.session.commit()

    return {"message": "Task created"}

@app.route("/tasks", methods=["GET"])
@jwt_required()
def get_tasks():
    tasks = Task.query.all()

    return [{"id": t.id, "title": t.title, "status": t.status} for t in tasks]

@app.route("/tasks/<int:id>", methods=["PUT"])
@jwt_required()
def update_task(id):
    data = request.get_json()

    task = Task.query.get(id)
    task.status = data["status"]

    db.session.commit()

    return {"message": "Task updated"}

# ================= DASHBOARD =================
@app.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    tasks = Task.query.all()

    total = len(tasks)
    completed = len([t for t in tasks if t.status == "Done"])
    pending = total - completed

    return {
        "total_tasks": total,
        "completed": completed,
        "pending": pending
    }

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=port)