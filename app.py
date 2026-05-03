from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'super-secret-key-change-in-prod')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
jwt = JWTManager(app)

# ─── MODELS ───────────────────────────────────────────────

class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100), nullable=False)
    email    = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role     = db.Column(db.String(20), default='Member')  # Admin / Member

class Project(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    description= db.Column(db.String(300), default='')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tasks      = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')

class Task(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), default='')
    project_id  = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status      = db.Column(db.String(20), default='Pending')  # Pending / In Progress / Done
    due_date    = db.Column(db.Date, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

# ─── HELPERS ──────────────────────────────────────────────

def get_current_user():
    uid = get_jwt_identity()
    return User.query.get(int(uid))

def task_to_dict(t):
    assignee = User.query.get(t.assigned_to) if t.assigned_to else None
    today = date.today()
    is_overdue = (
        t.due_date and
        t.due_date < today and
        t.status != 'Done'
    )
    return {
        'id': t.id,
        'title': t.title,
        'description': t.description,
        'project_id': t.project_id,
        'project_name': t.project.name if t.project else '',
        'assigned_to': t.assigned_to,
        'assignee_name': assignee.name if assignee else 'Unassigned',
        'status': t.status,
        'due_date': t.due_date.isoformat() if t.due_date else None,
        'is_overdue': is_overdue,
        'created_at': t.created_at.isoformat()
    }

# ─── AUTH ROUTES ──────────────────────────────────────────

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data received'}), 400

    name     = data.get('name', '').strip()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role     = data.get('role', 'Member')

    if not name or not email or not password:
        return jsonify({'error': 'Name, email and password are required'}), 400
    if role not in ('Admin', 'Member'):
        return jsonify({'error': 'Role must be Admin or Member'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400

    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Account created successfully'}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data received'}), 400

    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({
        'token': token,
        'role': user.role,
        'name': user.name,
        'id': user.id
    })


# ─── USER ROUTES ──────────────────────────────────────────

@app.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    users = User.query.all()
    return jsonify([{'id': u.id, 'name': u.name, 'email': u.email, 'role': u.role} for u in users])


# ─── PROJECT ROUTES ───────────────────────────────────────

@app.route('/projects', methods=['GET'])
@jwt_required()
def get_projects():
    projects = Project.query.all()
    result = []
    for p in projects:
        creator = User.query.get(p.created_by)
        result.append({
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'created_by': p.created_by,
            'creator_name': creator.name if creator else 'Unknown',
            'task_count': len(p.tasks),
            'created_at': p.created_at.isoformat()
        })
    return jsonify(result)


@app.route('/projects', methods=['POST'])
@jwt_required()
def create_project():
    user = get_current_user()
    if user.role != 'Admin':
        return jsonify({'error': 'Only Admin can create projects'}), 403

    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Project name is required'}), 400

    project = Project(
        name=name,
        description=data.get('description', ''),
        created_by=user.id
    )
    db.session.add(project)
    db.session.commit()
    return jsonify({'message': 'Project created', 'id': project.id}), 201


@app.route('/projects/<int:pid>', methods=['DELETE'])
@jwt_required()
def delete_project(pid):
    user = get_current_user()
    if user.role != 'Admin':
        return jsonify({'error': 'Only Admin can delete projects'}), 403

    project = Project.query.get_or_404(pid)
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted'})


# ─── TASK ROUTES ──────────────────────────────────────────

@app.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    user = get_current_user()

    # Admin sees all; Member sees only assigned tasks
    if user.role == 'Admin':
        tasks = Task.query.all()
    else:
        tasks = Task.query.filter_by(assigned_to=user.id).all()

    project_id = request.args.get('project_id')
    if project_id:
        tasks = [t for t in tasks if t.project_id == int(project_id)]

    return jsonify([task_to_dict(t) for t in tasks])


@app.route('/tasks', methods=['POST'])
@jwt_required()
def create_task():
    user = get_current_user()
    if user.role != 'Admin':
        return jsonify({'error': 'Only Admin can create tasks'}), 403

    data = request.get_json()
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': 'Task title is required'}), 400

    project = Project.query.get(data.get('project_id'))
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    due_date = None
    if data.get('due_date'):
        try:
            due_date = date.fromisoformat(data['due_date'])
        except ValueError:
            return jsonify({'error': 'Invalid due_date format (use YYYY-MM-DD)'}), 400

    task = Task(
        title=title,
        description=data.get('description', ''),
        project_id=data['project_id'],
        assigned_to=data.get('assigned_to'),
        status='Pending',
        due_date=due_date
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({'message': 'Task created', 'id': task.id}), 201


@app.route('/tasks/<int:tid>', methods=['PUT'])
@jwt_required()
def update_task(tid):
    user = get_current_user()
    task = Task.query.get_or_404(tid)

    # Members can only update status of their own tasks
    if user.role == 'Member' and task.assigned_to != user.id:
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()

    if 'status' in data:
        if data['status'] not in ('Pending', 'In Progress', 'Done'):
            return jsonify({'error': 'Invalid status'}), 400
        task.status = data['status']

    # Only admin can change assignment / due date / title
    if user.role == 'Admin':
        if 'title' in data:
            task.title = data['title'].strip()
        if 'description' in data:
            task.description = data['description']
        if 'assigned_to' in data:
            task.assigned_to = data['assigned_to']
        if 'due_date' in data:
            try:
                task.due_date = date.fromisoformat(data['due_date']) if data['due_date'] else None
            except ValueError:
                return jsonify({'error': 'Invalid due_date format'}), 400

    db.session.commit()
    return jsonify({'message': 'Task updated', 'task': task_to_dict(task)})


@app.route('/tasks/<int:tid>', methods=['DELETE'])
@jwt_required()
def delete_task(tid):
    user = get_current_user()
    if user.role != 'Admin':
        return jsonify({'error': 'Only Admin can delete tasks'}), 403

    task = Task.query.get_or_404(tid)
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted'})


# ─── DASHBOARD ────────────────────────────────────────────

@app.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    user = get_current_user()
    today = date.today()

    if user.role == 'Admin':
        tasks = Task.query.all()
    else:
        tasks = Task.query.filter_by(assigned_to=user.id).all()

    total     = len(tasks)
    done      = sum(1 for t in tasks if t.status == 'Done')
    in_prog   = sum(1 for t in tasks if t.status == 'In Progress')
    pending   = sum(1 for t in tasks if t.status == 'Pending')
    overdue   = sum(1 for t in tasks if t.due_date and t.due_date < today and t.status != 'Done')

    projects  = Project.query.count() if user.role == 'Admin' else None
    members   = User.query.filter_by(role='Member').count() if user.role == 'Admin' else None

    return jsonify({
        'total_tasks': total,
        'done': done,
        'in_progress': in_prog,
        'pending': pending,
        'overdue': overdue,
        'projects': projects,
        'members': members
    })


# ─── INIT ─────────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)