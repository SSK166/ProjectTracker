from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import sqlite3
import pandas as pd
from fastapi import Body
import os
from datetime import date 
from fastapi.responses import FileResponse

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
    
    # get all rows for the project
    rows = conn.execute("""
        SELECT p.id, p.project_name, p.packaging_type, p.packaging_option
        FROM projects p
        WHERE p.project_name = ?
    """, (project_name,)).fetchall()
    
    result = []
    today = date.today().isoformat()
    
    for row in rows:
        row_dict = dict(row)
        # for row_key in row_dict:
        #     print(f"Row Key:{row_key}")
        project_id = row_dict["id"]
        
        # get all status values for this row
        statuses = conn.execute("""
            SELECT column_name, current_value FROM status
            WHERE project_id = ?
        """, (project_id,)).fetchall()
        
        # get all deadlines for this row
        deadlines = conn.execute("""
            SELECT column_name, deadline FROM deadlines
            WHERE project_id = ?
        """, (project_id,)).fetchall()
        
        status_map = {s["column_name"]: s["current_value"] for s in statuses}
        deadline_map = {d["column_name"]: d["deadline"] for d in deadlines}
        
        # add status values to row
        for col in STATUS_COLUMNS:#explained in database.py status creation
            row_dict[col] = status_map.get(col, None)
        
        # calculate overall row health
        health = "green"
        TEXT_COLS = ["Dimensions", "Code Creation", "Specification", "BOM", "SOP"]
        for col, deadline in deadline_map.items():
            if col in TEXT_COLS:
                continue # we skip health calculation for text only fields
            current_val = status_map.get(col, "")
            is_complete = current_val in ["Approved", "Closed", "Dispatched", "Yes", "Received"]
            is_overdue = deadline and today > deadline
            
            if is_overdue and not is_complete:
                health = "red"
                break
            elif not is_complete and health != "red":
                health = "yellow"
        
        row_dict["_health"] = health
        result.append(row_dict)
    
    conn.close()
    # print(f"Project Rows for {project_name}: {result}")
    return result


@app.get("/api/status/{project_id}")
def get_status(project_id: int):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM status WHERE project_id = ?
    """, (project_id,)).fetchall()
    conn.close()
    # for row in rows:
    #     print(f"Status Row: {dict(row)}")
    return [dict(row) for row in rows]

@app.get("/api/deadlines/{project_id}")
def get_deadlines(project_id:int):
    conn=get_conn()
    selected=conn.execute("""
        SELECT column_name,deadline from deadlines WHERE project_id=?""",(project_id,)).fetchall()
    conn.close()
    return [dict(row)for row in selected]

@app.get("/api/alerts")
def get_alerts():
    conn = get_conn()
    today = date.today().isoformat()

    rows = conn.execute("""
        SELECT 
            p.id as project_id,
            p.project_name,
            p.packaging_type,
            p.packaging_option,
            s.column_name,
            s.current_value,
            d.deadline
        FROM deadlines d
        JOIN projects p ON p.id = d.project_id
        JOIN status s ON s.project_id = d.project_id 
            AND s.column_name = d.column_name
        WHERE d.deadline < ?
        AND s.current_value NOT IN ('Approved','Closed','Dispatched','Yes','Received')
        ORDER BY d.deadline ASC
    """, (today,)).fetchall()

    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/projects/id/{project_id}")
def get_project_by_id(project_id: int):
    conn = get_conn()
    today = date.today().isoformat()

    row = conn.execute("""
        SELECT * FROM projects WHERE id = ?
    """, (project_id,)).fetchone()

    conn.close()
    return dict(row)

@app.put("/api/status/{project_id}")
def update_status(project_id: int, data: dict = Body(...)):
    conn = get_conn()
    for col, value in data.items():
        conn.execute("""
            INSERT INTO status (project_id, column_name, current_value)
            VALUES (?, ?, ?)
            ON CONFLICT(project_id, column_name) DO UPDATE SET current_value = ?
        """, (project_id, col, value, value))
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

STATUS_COLUMNS = [
    "KLD Status",
    "Artwork Status", 
    "Artwork to Vendor Status",
    "Artwork to Vendor Status 2",
    "Dispatch Status",
    "Cost Closure Status",
    "Project Status",
    "Connectivity Status",
    "PDF Approved",
    "Dimensions",
    "Code Creation",
    "Specification",
    "BOM",
    "SOP"
]

BASE_COLUMNS=[
    "project_name",
    "packaging_type",
    "packaging_option"
]

@app.post("/api/projects")
def add_project(data: dict = Body(...)):
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO projects (project_name, packaging_type, packaging_option)
        VALUES (?, ?, ?)
    """, (data["project_name"], data["packaging_type"], data["packaging_option"]))
    
    project_id = cursor.lastrowid
    
    # initialize empty status rows for every status column
    for col in STATUS_COLUMNS:
        cursor.execute("""
            INSERT INTO status (project_id, column_name, current_value)
            VALUES (?, ?, NULL)
        """, (project_id, col))
    
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.delete("/api/projects/{project_id}")
def delete_project(project_id:int):
    conn=get_conn()
    conn.execute("DELETE FROM projects WHERE id=?",(project_id,))
    conn.execute("DELETE FROM status WHERE project_id=?",(project_id,))
    conn.execute("DELETE FROM deadlines WHERE project_id=?",(project_id,))
    conn.commit()
    conn.close()
    return {"status":"ok"}


@app.get("/api/download/{excel_name}")
def download_excel(excel_name: str):
    projects = get_projects()
    df = []
    for project in projects:
        df.extend(get_project_rows(project))
    df = pd.DataFrame(df)
    df = df[BASE_COLUMNS + STATUS_COLUMNS]
    
    prev = None
    for idx, row in df.iterrows():
        if row["project_name"] != prev:
            prev = row["project_name"]
        else:
            df.at[idx, "project_name"] = ""
    
    file_path = f"{excel_name}.xlsx"
    df.to_excel(file_path, index=False)
    
    return FileResponse(
        path=file_path,
        filename=f"{excel_name}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )