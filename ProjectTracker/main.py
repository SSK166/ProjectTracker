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
from fastapi import File, UploadFile
import tempfile

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
    "Code creation",
    "Specification",
    "BOM",
    "SOP"
]

BASE_COLUMNS = ["project_name", "packaging_type", "packaging_option"]

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
        SELECT p.id, p.project_name, p.packaging_type, p.packaging_option
        FROM projects p WHERE p.project_name = ?
    """, (project_name,)).fetchall()

    result = []
    today = date.today().isoformat()

    for row in rows:
        row_dict = dict(row)
        project_id = row_dict["id"]

        statuses = conn.execute("""
            SELECT column_name, current_value FROM status WHERE project_id = ?
        """, (project_id,)).fetchall()

        deadlines = conn.execute("""
            SELECT column_name, deadline FROM deadlines WHERE project_id = ?
        """, (project_id,)).fetchall()

        status_map = {s["column_name"].strip(): s["current_value"] for s in statuses}
        deadline_map = {d["column_name"].strip(): d["deadline"] for d in deadlines}

        for col in STATUS_COLUMNS:
            row_dict[col] = status_map.get(col, None)

        health = "green"
        TEXT_COLS = ["Dimensions", "Code creation", "Specification", "BOM", "SOP"]
        for col, deadline in deadline_map.items():
            if col in TEXT_COLS:
                continue
            current_val = status_map.get(col, "")
            is_complete = current_val in ["Approved", "Closed", "Dispatched", "Yes", "Received"]
            is_overdue = deadline and today > deadline

            if is_overdue and not is_complete:
                health = "red"
                break
            elif is_overdue and is_complete:
                health = "yellow"

        row_dict["_health"] = health
        result.append(row_dict)

    conn.close()
    return result

@app.get("/api/status/{project_id}")
def get_status(project_id: int):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM status WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/deadlines/{project_id}")
def get_deadlines(project_id: int):
    conn = get_conn()
    selected = conn.execute("""
        SELECT column_name, deadline FROM deadlines WHERE project_id = ?
    """, (project_id,)).fetchall()
    conn.close()
    return [dict(row) for row in selected]

@app.get("/api/alerts")
def get_alerts():
    conn = get_conn()
    today = date.today().isoformat()
    rows = conn.execute("""
        SELECT 
            p.id as project_id, p.project_name, p.packaging_type, p.packaging_option,
            s.column_name, s.current_value, d.deadline
        FROM deadlines d
        JOIN projects p ON p.id = d.project_id
        JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
        WHERE d.deadline < ?
        AND s.current_value NOT IN ('Approved','Closed','Dispatched','Yes','Received')
        ORDER BY d.deadline ASC
    """, (today,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/projects/id/{project_id}")
def get_project_by_id(project_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row)

@app.get("/api/due-today")
def get_due_today():
    conn = get_conn()
    today = date.today().isoformat()
    rows = conn.execute("""
        SELECT 
            p.id as project_id, p.project_name, p.packaging_type, p.packaging_option,
            s.column_name, s.current_value, d.deadline
        FROM deadlines d
        JOIN projects p ON p.id = d.project_id
        JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
        WHERE d.deadline = ?
        AND s.current_value NOT IN ('Approved','Closed','Dispatched','Yes','Received')
        ORDER BY p.project_name ASC
    """, (today,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.put("/api/status/{project_id}")
def update_status(project_id: int, data: dict = Body(...)):
    conn = get_conn()
    today = date.today().isoformat()
    GREEN_VALUES = ["Approved", "Closed", "Dispatched", "Yes", "Received"]

    for col, value in data.items():
        completion_date = today if value in GREEN_VALUES else None
        conn.execute("""
            INSERT INTO status (project_id, column_name, current_value, completion_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(project_id, column_name) DO UPDATE SET 
                current_value = ?,
                completion_date = CASE 
                    WHEN ? IN ('Approved','Closed','Dispatched','Yes','Received') 
                    THEN COALESCE(completion_date, ?)
                    ELSE NULL 
                END
        """, (project_id, col, value, completion_date, value, value, today))

    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.post("/api/deadlines/{project_id}")
def save_deadlines(project_id: int, data: dict = Body(...)):
    conn = get_conn()
    for col, deadline in data.items():
        if deadline:
            conn.execute("""
                INSERT INTO deadlines (project_id, column_name, deadline)
                VALUES (?, ?, ?)
                ON CONFLICT(project_id, column_name) DO UPDATE SET deadline = ?
            """, (project_id, col, deadline, deadline))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.post("/api/projects")
def add_project(data: dict = Body(...)):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO projects (project_name, packaging_type, packaging_option)
        VALUES (?, ?, ?)
    """, (data["project_name"], data["packaging_type"], data["packaging_option"]))
    project_id = cursor.lastrowid
    for col in STATUS_COLUMNS:
        cursor.execute("""
            INSERT INTO status (project_id, column_name, current_value)
            VALUES (?, ?, NULL)
        """, (project_id, col))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.execute("DELETE FROM status WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM deadlines WHERE project_id = ?", (project_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/download/{excel_name}")
def download_excel(excel_name: str):
    conn = get_conn()
    projects = get_projects()
    all_rows = []

    for project in projects:
        rows = conn.execute("""
            SELECT p.id, p.project_name, p.packaging_type, p.packaging_option
            FROM projects p WHERE p.project_name = ?
        """, (project,)).fetchall()

        for row in rows:
            row_dict = dict(row)
            project_id = row_dict["id"]

            statuses = conn.execute(
                "SELECT column_name, current_value, completion_date FROM status WHERE project_id = ?",
                (project_id,)
            ).fetchall()
            deadlines = conn.execute(
                "SELECT column_name, deadline FROM deadlines WHERE project_id = ?",
                (project_id,)
            ).fetchall()

            status_map = {s["column_name"]: s["current_value"] for s in statuses}
            completion_map = {s["column_name"]: s["completion_date"] for s in statuses}
            deadline_map = {d["column_name"]: d["deadline"] for d in deadlines}

            flat = {
                "project_name": row_dict["project_name"],
                "packaging_type": row_dict["packaging_type"],
                "packaging_option": row_dict["packaging_option"],
            }
            for col in STATUS_COLUMNS:
                flat[col] = status_map.get(col)
                flat[col + " | Deadline"] = deadline_map.get(col)
                flat[col + " | Completed On"] = completion_map.get(col)

            all_rows.append(flat)

    conn.close()

    df = pd.DataFrame(all_rows)
    file_path = f"{excel_name}.xlsx"
    df.to_excel(file_path, index=False, sheet_name="Project Tracker")  # fixed: named sheet

    return FileResponse(
        path=file_path,
        filename=f"{excel_name}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.post("/api/import")
async def import_excel(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        xl = pd.ExcelFile(tmp_path)
        sheet = "Project Tracker" if "Project Tracker" in xl.sheet_names else xl.sheet_names[0]
        df = xl.parse(sheet_name=sheet)
        xl.close()  # release file handle before finally

        # Detect format: original Excel uses "Project", export uses "project_name"
        if "Project" in df.columns:
            # Original Excel format
            df = df.rename(columns={
                "Project": "project_name",
                "Packaging Type": "packaging_type",
                "Packaging Option": "packaging_option",
                "Unnamed: 8": "Artwork to Vendor Status 2",
                "Code creation ": "Code creation"
            })
        # else: already in export format with project_name, packaging_type, packaging_option

        df["project_name"] = df["project_name"].ffill()
        df["Code creation"] = df["Code creation"].apply(
            lambda x: str(int(x)) if pd.notna(x) else None
        )
        conn = get_conn()
        cursor = conn.cursor()
        rows_imported = 0
        GREEN_VALUES = ["Approved", "Closed", "Dispatched", "Yes", "Received"]

        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO projects (project_name, packaging_type, packaging_option)
                VALUES (?, ?, ?)
            """, (
                row.get("project_name"),      # fixed: was row.get("Project")
                row.get("packaging_type"),    # fixed: was row.get("Packaging Type")
                row.get("packaging_option")   # fixed: was row.get("Packaging Option")
            ))
            project_id = cursor.lastrowid

            for col in STATUS_COLUMNS:
                value = row.get(col)
                value = str(value) if pd.notna(value) else None

                completion_col = col + " | Completed On"
                completion_date = None
                if completion_col in df.columns:
                    raw = row.get(completion_col)
                    if pd.notna(raw):
                        try:
                            completion_date = pd.to_datetime(raw).date().isoformat()
                        except Exception:
                            completion_date = None

                if completion_date is None and value in GREEN_VALUES:
                    completion_date = date.today().isoformat()

                cursor.execute("""
                    INSERT INTO status (project_id, column_name, current_value, completion_date)
                    VALUES (?, ?, ?, ?)
                """, (project_id, col, value, completion_date))

                deadline_col = col + " | Deadline"
                if deadline_col in df.columns:
                    raw_deadline = row.get(deadline_col)
                    if pd.notna(raw_deadline):
                        try:
                            deadline_str = pd.to_datetime(raw_deadline).date().isoformat()
                            cursor.execute("""
                                INSERT INTO deadlines (project_id, column_name, deadline)
                                VALUES (?, ?, ?)
                                ON CONFLICT(project_id, column_name) DO UPDATE SET deadline = ?
                            """, (project_id, col, deadline_str, deadline_str))
                        except Exception:
                            pass

            rows_imported += 1

        conn.commit()
        conn.close()

    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    return {"status": "ok", "rows_imported": rows_imported}