# ⚡ TaskFlow — Team Task Manager

A full-stack task management app with role-based access control (Admin/Member).

## 🚀 Live Demo
https://team-task-manager-production-fd26.up.railway.app/

## 📦 Tech Stack
- **Backend**: Python / Flask, Flask-JWT-Extended, SQLAlchemy, SQLite
- **Frontend**: Vanilla HTML/CSS/JS (single file)
- **Deployment**: Railway

## ✨ Features
- 🔐 JWT Authentication (Signup / Login / Logout)
- 👥 Role-based access — Admin & Member
- 📁 Project management (Admin only)
- ✅ Task creation, assignment & status tracking
- 📊 Dashboard with stats (total, done, pending, overdue)
- 🔴 Overdue task detection via due dates
- 🏷️ Filter tasks by status or project

## 👤 Role Permissions

| Feature            | Admin | Member |
|--------------------|-------|--------|
| Create Project     | ✅    | ❌     |
| Delete Project     | ✅    | ❌     |
| Create Task        | ✅    | ❌     |
| Delete Task        | ✅    | ❌     |
| Update Task Status | ✅    | ✅ (own tasks) |
| View All Tasks     | ✅    | ❌ (own only) |
| View Members       | ✅    | ❌     |

## ⚙️ Local Setup

```bash
# Clone
git clone <your-repo-url>
cd taskflow

# Install dependencies
pip install -r requirements.txt

# Run
python app.py
```

Open `index.html` in browser (or serve it via a static server).  
API runs at `http://localhost:5000`

## 🌐 Railway Deployment

1. Push to GitHub
2. Create new project on [Railway](https://railway.app)
3. Connect GitHub repo → Railway auto-detects `Procfile`
4. Add environment variables:
   - `JWT_SECRET_KEY` = some-long-random-string
5. Deploy — Railway gives you a live URL
6. Update `API` variable in `index.html` to point to your Railway URL

## 📡 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/signup` | No | Register user |
| POST | `/login` | No | Login, get JWT |
| GET | `/users` | Yes | List all users |
| GET | `/projects` | Yes | List projects |
| POST | `/projects` | Admin | Create project |
| DELETE | `/projects/:id` | Admin | Delete project |
| GET | `/tasks` | Yes | List tasks |
| POST | `/tasks` | Admin | Create task |
| PUT | `/tasks/:id` | Yes | Update task |
| DELETE | `/tasks/:id` | Admin | Delete task |
| GET | `/dashboard` | Yes | Stats summary |
