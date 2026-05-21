from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import sqlite3
import pandas as pd
from fastapi import Body
import os

app = FastAPI()
print("Running from:", os.getcwd())
print("DB PATH:", os.path.join(os.path.dirname(__file__), "projects.db"))

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_PATH = os.path.join(os.path.dirname(__file__), "projects.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/api/projects")
def get_projects():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT project_name FROM projects").fetchall()
    conn.close()
    return [row["project_name"] for row in rows]

@app.get("/api/projects/{project_name}")
def get_project_rows(project_name: str):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM projects WHERE project_name = ?
    """, (project_name,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/status/{project_id}")
def get_status(project_id: int):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM status WHERE project_id = ?
    """, (project_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/deadlines/{project_id}")
def get_deadlines(project_id:int):
    conn=get_conn()
    selected=conn.execute("""
        SELECT column_name,deadline from deadlines WHERE project_id=?""",(project_id,)).fetchall()
    conn.close()
    return [dict(row)for row in selected]

@app.put("/api/status/{project_id}")
def update_status(project_id: int, data: dict = Body(...)):
    conn = get_conn()
    for col, value in data.items():
        conn.execute("""
            UPDATE status SET current_value = ?
            WHERE project_id = ? AND column_name = ?
        """, (value, project_id, col))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.post("/api/deadlines/{project_id}")
def save_deadlines(project_id:int,data:dict=Body(...)):
    conn=get_conn()
    for col,deadline in data.items():
        if deadline:
            conn.execute("""
                INSERT INTO deadlines (project_id, column_name, deadline)
                VALUES (?, ?, ?)
                ON CONFLICT(project_id, column_name) DO UPDATE SET deadline = ?
            """, (project_id, col, deadline, deadline))#On conflict to update the deadline if it alread exists

    conn.commit()
    conn.close()
    return {"status":"ok"}

