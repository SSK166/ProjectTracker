from fastapi import APIRouter, Body, File, UploadFile, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import FileResponse
import psycopg2
import psycopg2.extras
import pandas as pd
import os
import tempfile
from datetime import date,datetime
from dotenv import load_dotenv
import tempfile
from starlette.background import BackgroundTask
import openpyxl
from openpyxl.utils import get_column_letter

from dependencies import get_current_user,verify_roles,get_ist_date
from userdb import User

load_dotenv()

STATUS_COLUMNS = [
    "KLD Status",
    "Artwork Status",
    "Sampling Status",
    "Commercial Ordering Status",
    "Connectivity Status",
    "Project Status"
]


router=APIRouter()

#Pooling connections for handling load of simultaneous access by multiple users

tracker_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=2,
    maxconn=10,
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("GROWTH_DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    sslmode= "require" if os.getenv('ENVIRONMENT') else "disable"
)

def get_conn():
    return tracker_pool.getconn()
def dict_cursor(conn):
    # psycopg2 equivalent of sqlite3's row_factory
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


@router.get("/api/projects")
def get_projects(current_user:User=Depends(get_current_user)):
    conn = get_conn()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT project_name,MIN(id) FROM projects GROUP BY project_name ORDER BY MIN(id) ASC")
        rows = cur.fetchall()
        cur.close()
        return [row["project_name"] for row in rows]
    finally:
        if conn:
            tracker_pool.putconn(conn)
    

@router.get("/api/projects/id/{project_id}")
def get_project_by_id(project_id: int,current_user:User=Depends(get_current_user)):
    conn = get_conn()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        row = cur.fetchone()
        cur.close()
        return dict(row)
    finally:
        if conn:
            tracker_pool.putconn(conn)
    

@router.get("/api/projects/{project_name}")
def get_project_rows(project_name: str,current_user:User=Depends(get_current_user)):
    conn = get_conn()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT p.id, p.project_name, p.packaging_type, p.packaging_option
            FROM projects p WHERE p.project_name = %s ORDER BY p.id ASC
        """, (project_name,))
        rows = cur.fetchall()

        result = []
        today = get_ist_date().isoformat()
        # TEXT_COLS = ["Project Status"]

        for row in rows:
            row_dict = dict(row)
            project_id = row_dict["id"]

            cur.execute("SELECT column_name, current_value FROM status WHERE project_id = %s", (project_id,))
            statuses = cur.fetchall()

            cur.execute("SELECT column_name, deadline FROM deadlines WHERE project_id = %s", (project_id,))
            deadlines = cur.fetchall()

            status_map = {s["column_name"].strip(): s["current_value"] for s in statuses}
            deadline_map = {
                d["column_name"].strip(): (str(d["deadline"]) if d["deadline"] is not None else None) 
                for d in deadlines
            }
            # str() needed — psycopg2 returns deadline as a Python date object, not string

            for col in STATUS_COLUMNS:
                row_dict[col] = status_map.get(col, None)

            red_cols = []
            yellow_cols = []
            for col, deadline in deadline_map.items():
                current_val = status_map.get(col, "")
                if col == "Project Status":
                    is_complete=(current_val=="Completed")
                else:
                    is_complete = current_val in  ["Received", "Connected", "Completed", "KLD Shared"]
                    
                is_overdue = deadline and today > deadline

                if is_overdue and not is_complete:
                    red_cols.append(col)
                elif is_overdue and is_complete:
                    yellow_cols.append(col)

            row_dict["red_cols"] = red_cols
            row_dict["yellow_cols"] = yellow_cols
            row_dict["_health"] = "green"
            result.append(row_dict)

        cur.close()
        return result
    finally:
        if conn:
            tracker_pool.putconn(conn)
    

@router.get("/api/status/{project_id}")
def get_status(project_id: int,current_user:User=Depends(get_current_user)):
    conn = get_conn()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM status WHERE project_id = %s", (project_id,))
        rows = cur.fetchall()
        cur.close()
        return [dict(row) for row in rows]
    finally:
        if conn:
            tracker_pool.putconn(conn)
    

@router.get("/api/deadlines/{project_id}")
def get_deadlines(project_id: int,current_user:User=Depends(get_current_user)):
    conn = get_conn()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT column_name, deadline FROM deadlines WHERE project_id = %s", (project_id,))
        rows = cur.fetchall()
        cur.close()
        # Convert date objects to strings for JSON serialisation
        return [{"column_name": r["column_name"], "deadline": str(r["deadline"]) if r["deadline"] else ""} for r in rows]
    finally:
        if conn:
            tracker_pool.putconn(conn)
    

@router.get("/api/alerts")
def get_alerts(current_user:User=Depends(get_current_user)):
    conn = get_conn()
    try:
        cur = dict_cursor(conn)
        today = get_ist_date().isoformat()
        cur.execute("""
            SELECT p.id as project_id, p.project_name, p.packaging_type, p.packaging_option,
                s.column_name, s.current_value, d.deadline
            FROM deadlines d
            JOIN projects p ON p.id = d.project_id
            JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
            WHERE d.deadline < %s
            AND (s.current_value IS NULL OR s.current_value NOT IN ('Received', 'Connected', 'Completed', 'KLD Shared'))
            ORDER BY d.deadline ASC
        """, (today,))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) | {"deadline": str(r["deadline"])} for r in rows]
    finally:
        if conn:
            tracker_pool.putconn(conn)
    

@router.get("/api/alerts/{project_name}")
def get_alerts_for_project(project_name: str,current_user:User=Depends(get_current_user)):
    conn = get_conn()
    try:
        cur = dict_cursor(conn)
        today = get_ist_date().isoformat()
        cur.execute("""
            SELECT p.id as project_id, p.project_name, p.packaging_type, p.packaging_option,
                s.column_name, s.current_value, d.deadline
            FROM deadlines d
            JOIN projects p ON p.id = d.project_id
            JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
            WHERE d.deadline < %s 
            AND p.project_name = %s
            AND (s.current_value IS NULL OR s.current_value NOT IN ('Received', 'Connected', 'Completed', 'KLD Shared'))
            ORDER BY d.deadline ASC
        """, (today, project_name))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) | {"deadline": str(r["deadline"])} for r in rows]
    finally:
        if conn:
            tracker_pool.putconn(conn)
    



@router.get("/api/due-today")
def get_due_today(current_user:User=Depends(get_current_user)):
    conn = get_conn()
    try:
        cur = dict_cursor(conn)
        today = get_ist_date().isoformat()
        cur.execute("""
            SELECT p.id as project_id, p.project_name, p.packaging_type, p.packaging_option,
                s.column_name, s.current_value, d.deadline
            FROM deadlines d
            JOIN projects p ON p.id = d.project_id
            JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
            WHERE d.deadline = %s
            AND (s.current_value IS NULL OR s.current_value NOT IN ('Received', 'Connected', 'Completed', 'KLD Shared'))
            ORDER BY p.project_name ASC
        """, (today,))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) | {"deadline": str(r["deadline"])} for r in rows]
    finally:
        if conn:
            tracker_pool.putconn(conn)
    

@router.get("/api/due-today/{project_name}")
def get_due_today_for_project(project_name: str,current_user:User=Depends(get_current_user)):
    conn = get_conn()
    try:
        cur = dict_cursor(conn)
        today = get_ist_date().isoformat()
        cur.execute("""
            SELECT p.id as project_id, p.project_name, p.packaging_type, p.packaging_option,
                s.column_name, s.current_value, d.deadline
            FROM deadlines d
            JOIN projects p ON p.id = d.project_id
            JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
            WHERE d.deadline = %s 
            AND p.project_name = %s
            AND (s.current_value IS NULL OR s.current_value NOT IN ('Received', 'Connected', 'Completed', 'KLD Shared'))
            ORDER BY d.deadline ASC
        """, (today, project_name))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) | {"deadline": str(r["deadline"])} for r in rows]
    finally:
        if conn:
            tracker_pool.putconn(conn)
    

@router.put("/api/status/{project_id}")
def update_status(project_id: int, data: dict = Body(...),current_user:User=Depends(verify_roles(["admin","manager34"]))):
    conn = get_conn()
    try:
        cur = conn.cursor()
        today = get_ist_date().isoformat()
        GREEN_VALUES = ["Received", "Connected", "Completed", "KLD Shared"]

        for col, value in data.items():
        # fetch existing state first
            cur2 = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur2.execute("SELECT current_value, completion_date FROM status WHERE project_id=%s AND column_name=%s", (project_id, col))
            existing = cur2.fetchone()
            cur2.close()

            was_green = existing and existing["current_value"] in GREEN_VALUES
            is_green = value in GREEN_VALUES

            if is_green and not was_green:
                completion_date = today       # newly completed → stamp today
            elif is_green and was_green:
                completion_date = existing["completion_date"]  # preserve (even if NULL)
            else:
                completion_date = None        # not complete

            cur.execute("""
                INSERT INTO status (project_id, column_name, current_value, completion_date)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(project_id, column_name) DO UPDATE SET
                    current_value = EXCLUDED.current_value,
                    completion_date = EXCLUDED.completion_date
            """, (project_id, col, value, completion_date))
        # Note: PostgreSQL ON CONFLICT syntax uses EXCLUDED.column instead of bare values

        conn.commit()
        cur.close()
        return {"status": "ok"}
    finally:
        if conn:
            tracker_pool.putconn(conn)
    

@router.post("/api/deadlines/{project_id}")
def save_deadlines(project_id: int, data: dict = Body(...),current_user:User=Depends(verify_roles(["admin"]))):
    conn = get_conn()
    try:
        cur = conn.cursor()
        for col, deadline in data.items():
            if deadline:
                cur.execute("""
                    INSERT INTO deadlines (project_id, column_name, deadline)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(project_id, column_name) DO UPDATE SET deadline = EXCLUDED.deadline
                """, (project_id, col, deadline))
        conn.commit()
        cur.close()
        return {"status": "ok"}
    finally:
        if conn:
            tracker_pool.putconn(conn)
    

@router.post("/api/projects")
def add_project(data: dict = Body(...),current_user:User=Depends(verify_roles(["admin","manager34"]))):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO projects (project_name, packaging_type, packaging_option)
            VALUES (%s, %s, %s) RETURNING id
        """, (data["project_name"], data["packaging_type"], data["packaging_option"]))
        project_id = cur.fetchone()[0]
        for col in STATUS_COLUMNS:
            cur.execute("""
                INSERT INTO status (project_id, column_name, current_value)
                VALUES (%s, %s, NULL)
            """, (project_id, col))
        conn.commit()
        cur.close()
        return {"status": "ok"}
    finally:
        if conn:
            tracker_pool.putconn(conn)
    

@router.delete("/api/projects/{project_id}")
def delete_project(project_id: int,current_user:User=Depends(verify_roles(["admin","manager34"]))):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
        conn.commit()
        cur.close()
        return {"status": "ok"}
    finally:
        if conn:
            tracker_pool.putconn(conn)

@router.delete("/api/projects")
def delete_all_projects(current_user:User=Depends(verify_roles(["admin","manager34"]))):  # change role per tracker
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM deadlines")
        cur.execute("DELETE FROM status")
        cur.execute("DELETE FROM projects")  # cascades to status & deadlines if FK is set up with ON DELETE CASCADE
        conn.commit()
        cur.close()
        return {"status": "ok", "message": "All projects deleted"}
    finally:
        if conn:
            tracker_pool.putconn(conn)    

@router.get("/api/download/{excel_name}")
def download_excel(excel_name: str,current_user:User=Depends(verify_roles(["admin","manager34"]))):
    conn = get_conn()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT DISTINCT project_name,MIN(id) FROM projects GROUP BY project_name ORDER BY MIN(id) ASC")
        projects = [r["project_name"] for r in cur.fetchall()]
        all_rows = []

        for project in projects:
            cur.execute("""
                SELECT p.id, p.project_name, p.packaging_type, p.packaging_option
                FROM projects p WHERE p.project_name = %s
            """, (project,))
            rows = cur.fetchall()

            for row in rows:
                project_id = row["id"]
                cur.execute("SELECT column_name, current_value, completion_date FROM status WHERE project_id = %s", (project_id,))
                statuses = cur.fetchall()
                cur.execute("SELECT column_name, deadline FROM deadlines WHERE project_id = %s", (project_id,))
                deadlines = cur.fetchall()

                status_map = {s["column_name"]: s["current_value"] for s in statuses}
                completion_map = {s["column_name"]: str(s["completion_date"]) if s["completion_date"] else None for s in statuses}
                deadline_map = {d["column_name"]: str(d["deadline"]) if d["deadline"] else None for d in deadlines}

                flat = {
                    "project_name": row["project_name"],
                    "packaging_type": row["packaging_type"],
                    "packaging_option": row["packaging_option"],
                }
                for col in STATUS_COLUMNS:
                    flat[col] = status_map.get(col)
                    flat[col + " | Deadline"] = deadline_map.get(col)
                    flat[col + " | Completed On"] = completion_map.get(col)
                all_rows.append(flat)

        cur.close()
        df = pd.DataFrame(all_rows)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp_path = tmp.name

        df.to_excel(tmp_path, index=False, sheet_name="Project Tracker")
        
        return FileResponse(
            path=tmp_path,
            filename=f"{excel_name}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            background=BackgroundTask(os.remove, tmp_path)
        )
    finally:
        if conn:
            tracker_pool.putconn(conn)

    

@router.post("/api/import")
async def import_excel(file: UploadFile = File(...),mode:str="append",current_user:User=Depends(verify_roles(["admin","manager34"]))):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name
    conn = None
    try:
        xl = pd.ExcelFile(tmp_path)
        sheet = xl.sheet_names[0]
        df = xl.parse(sheet_name=sheet)
        xl.close()
        df.columns=df.columns.str.strip()
        if "Project Description" in df.columns:#Project Description
            df = df.rename(columns={
                "Project Description": "project_name",
                "Packaging Type": "packaging_type",
                "Packaging Option": "packaging_option",
                "KLD":"KLD Status",
                "Artwork":"Artwork Status",
                "Sampling":"Sampling Status",
                "Commercial Ordering":"Commercial Ordering Status",
                "Connectivity":"Connectivity Status"
                ,"Status":"Project Status"
            })
        df["project_name"] = df["project_name"].ffill()
        conn = get_conn()
        cur = conn.cursor()
        rows_imported = 0
        GREEN_VALUES = ["Received", "Connected", "Completed", "KLD Shared"]
        if mode == "overwrite":
            cur.execute("DELETE FROM projects")  # cascades if FK set up, else delete status/deadlines first
            conn.commit()
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO projects (project_name, packaging_type, packaging_option)
                VALUES (%s, %s, %s) RETURNING id
            """, (row.get("project_name"), row.get("packaging_type"), row.get("packaging_option")))
            project_id = cur.fetchone()[0]

            for col in STATUS_COLUMNS:
                value = row.get(col)
                value = str(value) if pd.notna(value) else None

                completion_date = None
                completion_col = col + " | Completed On"
                if completion_col in df.columns:
                    raw = row.get(completion_col)
                    if pd.notna(raw):
                        try:
                            completion_date = pd.to_datetime(raw).date().isoformat()
                        except Exception:
                            pass

                # if completion_date is None and value in GREEN_VALUES:
                #     completion_date = get_ist_date().isoformat()

                cur.execute("""
                    INSERT INTO status (project_id, column_name, current_value, completion_date)
                    VALUES (%s, %s, %s, %s)
                """, (project_id, col, value, completion_date))

                deadline_col = col + " | Deadline"
                if deadline_col in df.columns:
                    raw_deadline = row.get(deadline_col)
                    if pd.notna(raw_deadline):
                        try:
                            deadline_str = pd.to_datetime(raw_deadline).date().isoformat()
                            cur.execute("""
                                INSERT INTO deadlines (project_id, column_name, deadline)
                                VALUES (%s, %s, %s)
                                ON CONFLICT(project_id, column_name) DO UPDATE SET deadline = EXCLUDED.deadline
                            """, (project_id, col, deadline_str))
                        except Exception:
                            pass

            rows_imported += 1

        conn.commit()
        cur.close()
        return {"status": "ok", "rows_imported": rows_imported}

    finally:
        if conn:
            tracker_pool.putconn(conn)
        try:
            os.remove(tmp_path)
        except Exception:
            pass