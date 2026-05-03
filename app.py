from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import os

app = Flask(__name__)
CORS(app)

# ================= CONFIG =================
DATABASE_URL = os.environ.get('DATABASE_URL')

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
    description = db.Column(db.String(300))
    created_by = db.Column(db.Integer)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.String(300))
    project_id = db.Column(db.Integer)
    assigned_to = db.Column(db.Integer)
    assigned_by = db.Column(db.Integer)   # ✅ FIX ADDED
    status = db.Column(db.String(20), default="Pending")
    due_date = db.Column(db.String(20))

# ================= FRONTEND =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= DB INIT =================
@app.route("/init-db")
def init_db():
    db.create_all()
    return {"message": "Tables created successfully"}

# ================= AUTH =================
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "Member")

    if not name or not email or not password:
        return {"error": "Missing required fields"}, 400

    if User.query.filter_by(email=email).first():
        return {"error": "User already exists"}, 400

    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        role=role
    )

    db.session.add(user)
    db.session.commit()

    return {"message": "User created successfully"}

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    user = User.query.filter_by(email=data.get("email")).first()

    if not user or not check_password_hash(user.password, data.get("password")):
        return {"error": "Invalid credentials"}, 401

    token = create_access_token(identity=str(user.id))

    return {
        "token": token,
        "id": user.id,
        "name": user.name,
        "role": user.role
    }

# ================= PROJECT =================
@app.route("/projects", methods=["POST"])
@jwt_required()
def create_project():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    project = Project(
        name=data.get("name"),
        description=data.get("description", ""),
        created_by=user_id
    )

    db.session.add(project)
    db.session.commit()

    return {"message": "Project created successfully"}

@app.route("/projects", methods=["GET"])
@jwt_required()
def get_projects():
    projects = Project.query.all()
    result = []

    for p in projects:
        creator = User.query.get(p.created_by)
        task_count = Task.query.filter_by(project_id=p.id).count()

        result.append({
            "id": p.id,
            "name": p.name,
            "description": p.description or "",
            "task_count": task_count,
            "creator_name": creator.name if creator else "Unknown"
        })

    return result

@app.route("/projects/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_project(id):
    Task.query.filter_by(project_id=id).delete()

    project = Project.query.get(id)
    if not project:
        return {"error": "Project not found"}, 404

    db.session.delete(project)
    db.session.commit()

    return {"message": "Project deleted"}

# ================= TASK =================
@app.route("/tasks", methods=["POST"])
@jwt_required()
def create_task():
    data = request.get_json()
    user_id = int(get_jwt_identity())

    task = Task(
        title=data.get("title"),
        description=data.get("description", ""),
        project_id=data.get("project_id"),
        assigned_to=data.get("assigned_to"),
        assigned_by=user_id,   # ✅ FIX
        status="Pending",
        due_date=data.get("due_date")
    )

    db.session.add(task)
    db.session.commit()

    return {"message": "Task created successfully"}

@app.route("/tasks", methods=["GET"])
@jwt_required()
def get_tasks():
    tasks = Task.query.all()
    today = str(date.today())
    result = []

    for t in tasks:
        assignee = User.query.get(t.assigned_to) if t.assigned_to else None
        assigner = User.query.get(t.assigned_by) if t.assigned_by else None
        project = Project.query.get(t.project_id) if t.project_id else None

        is_overdue = bool(t.due_date and t.due_date < today and t.status != "Done")

        result.append({
            "id": t.id,
            "title": t.title,
            "description": t.description or "",
            "status": t.status,
            "due_date": t.due_date,
            "project_id": t.project_id,
            "project_name": project.name if project else "—",
            "assigned_to": t.assigned_to,
            "assignee_name": assignee.name if assignee else "Unassigned",
            "assigned_by": t.assigned_by,
            "assigned_by_name": assigner.name if assigner else "Unknown",  # ✅ FIX
            "is_overdue": is_overdue
        })

    return result

@app.route("/tasks/<int:id>", methods=["PUT"])
@jwt_required()
def update_task(id):
    data = request.get_json()

    task = Task.query.get(id)
    if not task:
        return {"error": "Task not found"}, 404

    task.status = data.get("status")
    db.session.commit()

    return {"message": "Task updated successfully"}

@app.route("/tasks/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_task(id):
    task = Task.query.get(id)
    if not task:
        return {"error": "Task not found"}, 404

    db.session.delete(task)
    db.session.commit()

    return {"message": "Task deleted"}

# ================= USERS =================
@app.route("/users", methods=["GET"])
@jwt_required()
def get_users():
    users = User.query.all()
    today = str(date.today())
    result = []

    for u in users:
        tasks = Task.query.filter_by(assigned_to=u.id).all()
        task_list = []

        for t in tasks:
            project = Project.query.get(t.project_id)
            assigner = User.query.get(t.assigned_by)

            is_overdue = bool(t.due_date and t.due_date < today and t.status != "Done")

            task_list.append({
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "due_date": t.due_date,
                "project_name": project.name if project else "—",
                "assigned_by_name": assigner.name if assigner else "Unknown",
                "is_overdue": is_overdue
            })

        result.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "tasks": task_list
        })

    return result

# ================= DASHBOARD =================
@app.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    tasks = Task.query.all()
    today = str(date.today())

    return {
        "total_tasks": len(tasks),
        "done": len([t for t in tasks if t.status == "Done"]),
        "in_progress": len([t for t in tasks if t.status == "In Progress"]),
        "pending": len([t for t in tasks if t.status == "Pending"]),
        "overdue": len([t for t in tasks if t.due_date and t.due_date < today and t.status != "Done"]),
        "projects": Project.query.count(),
        "members": User.query.count()
    }

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=port)