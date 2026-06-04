from fastapi import APIRouter, Body, File, UploadFile, Depends, Form,HTTPException
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

from dependencies import get_current_user,verify_roles
from userdb import User,UserDB

router=APIRouter()
db=UserDB()

tracker_db_params={"host":os.getenv('DB_HOST'),
            "port":os.getenv('DB_PORT'),
            "user":os.getenv('DB_USER'),
            "password":os.getenv('DB_PASSWORD')}



def get_conn(tracker:str):
    if(tracker=="project_tracker"):
        db_name="PROJECT_DB_NAME"
    elif(tracker=="growth_tracker"):
        db_name="GROWTH_DB_NAME"
    elif(tracker=="ve_tracker"):
        db_name="VALUE_DB_NAME"
    else:
        pass
    tracker_db_params["dbname"] = os.getenv(db_name)  
    conn = psycopg2.connect(**tracker_db_params)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn

@router.get("/summary")
def get_central_summary(current_user: User = Depends(verify_roles(["admin"]))):
    today = date.today().isoformat()
    summary_data = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "trackers": {}
    }
    
    # --- SCANNING PROJECT TRACKER ---
    try:
        from ProjectTracker.projectMain import get_conn as t1_conn
        with t1_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM projects")
                t1_total = cur.fetchone()[0]
                cur.execute("""
                    SELECT COUNT(*) FROM deadlines d
                    JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                    WHERE d.deadline < %s AND s.current_value NOT IN ('Approved','Closed','Dispatched','Yes','Received')
                """, (today,))
                t1_alerts = cur.fetchone()[0]
                cur.execute("""
                    SELECT COUNT(*) FROM deadlines d
                    JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                    WHERE d.deadline = %s AND s.current_value NOT IN ('Approved','Closed','Dispatched','Yes','Received')
                """, (today,))
                t1_due_today = cur.fetchone()[0]
                cur.execute("""
                    SELECT count(*) FROM status 
                    WHERE completion_date = %s
                """,(today,))
                t1_completed_today=cur.fetchone()[0]
        summary_data["trackers"]["project_tracker"] = {"name": "Project Tracker", "total": t1_total, "alerts": t1_alerts, "due_today":t1_due_today,"completed_today":t1_completed_today}
    except Exception as e:
        summary_data["trackers"]["project_tracker"] = {"error": f"Database offline: {str(e)}"}

    # --- SCANNING GROWTH TRACKER ---
    try:
        from GrowthTracker.growthMain import get_conn as t3_conn
        with t3_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM projects")
                t3_total = cur.fetchone()[0]
                cur.execute("""
                    SELECT COUNT(*) FROM deadlines d
                    JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                    WHERE d.deadline < %s AND s.current_value NOT IN ('Received', 'Connected', 'Completed', 'KLD Shared')
                """, (today,))
                t3_alerts = cur.fetchone()[0]
                cur.execute("""
                    SELECT COUNT(*) FROM deadlines d
                    JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                    WHERE d.deadline = %s AND s.current_value NOT IN ('Received', 'Connected', 'Completed', 'KLD Shared')
                """, (today,))
                t3_due_today = cur.fetchone()[0]
                cur.execute("""
                    SELECT count(*) FROM status 
                    WHERE completion_date = %s
                """,(today,))
                t3_completed_today=cur.fetchone()[0]
        summary_data["trackers"]["growth_tracker"] = {"name": "Growth Tracker", "total": t3_total, "alerts": t3_alerts, "due_today":t3_due_today,"completed_today":t3_completed_today}
    except Exception as e:
        summary_data["trackers"]["growth_tracker"] = {"error": f"Database offline: {str(e)}"}

    # --- SCANNING VALUE ENGINEERING TRACKER ---
    try:
        from VETracker.valueMain import get_conn as t4_conn
        with t4_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM projects")
                t4_total = cur.fetchone()[0]
                cur.execute("""
                    SELECT COUNT(*) FROM deadlines d
                    JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                    WHERE d.deadline < %s AND s.current_value NOT IN ('Completed','Shared')
                """, (today,))
                t4_alerts = cur.fetchone()[0]
                cur.execute("""
                    SELECT COUNT(*) FROM deadlines d
                    JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                    WHERE d.deadline = %s AND s.current_value NOT IN ('Completed','Shared')
                """, (today,))
                t4_due_today = cur.fetchone()[0]
                cur.execute("""
                    SELECT count(*) FROM status 
                    WHERE completion_date = %s
                """,(today,))
                t4_completed_today=cur.fetchone()[0]
        summary_data["trackers"]["ve_tracker"] = {"name": "Value Engineering Tracker", "total": t4_total, "alerts": t4_alerts, "due_today":t4_due_today,"completed_today":t4_completed_today}
    except Exception as e:
        summary_data["trackers"]["ve_tracker"] = {"error": f"Database offline: {str(e)}"}

    return summary_data

@router.put("/role")
def update_role(username:str=Form(...),role:str=Form(...),current_user:User=Depends(verify_roles(["admin"]))):
    existing_user=db.get_by_username(username)
    if not existing_user:
        raise HTTPException(
            status_code=404,
            detail="No user found. Enter the right username"
        )
    switch=db.switch_role(existing_user.id,role)
    if not switch:
        raise HTTPException(
            status_code=500,
            detail="Server Error Role could not be updated"
        )
    return {"status":"success","message":f"User role updated to {role}"}

@router.get("/last-7-days/{tracker}")
def get_completed_last_7(tracker:str,current_user: User = Depends(verify_roles(["admin"]))):
    try:
        with get_conn(tracker) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) AS total_count FROM status 
                    WHERE completion_date >= CURRENT_DATE - INTERVAL '7 days'
                """)
                result=cur.fetchone()
                count = result["total_count"] if result else 0
        return {"completed_last_7": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database execution trace failure: {str(e)}")
    
@router.get("/upcoming/{tracker}")
def get_upcoming_deadlines(tracker:str,current_user: User = Depends(verify_roles(["admin"]))):
    try:
        with get_conn(tracker) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT p.project_name, d.column_name, s.current_value, d.deadline 
                    FROM deadlines d
                    JOIN projects p ON p.id = d.project_id
                    JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                    WHERE d.deadline > CURRENT_DATE 
                      AND d.deadline <= CURRENT_DATE + INTERVAL '7 days'
                      AND s.current_value NOT IN ('Approved','Closed','Dispatched','Completed','Shared','Received','Yes')
                    ORDER BY d.deadline ASC
                """)
                rows = cur.fetchall()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database execution trace failure: {str(e)}")

@router.get("/7-days-projects/{tracker}")
def get_last_7_days_projects_(tracker:str,current_user: User = Depends(verify_roles(["admin"]))):
    try:
        with get_conn(tracker) as conn:
            with conn.cursor() as cur:
                if tracker=="project_tracker":
                    col="Project Status"
                    val="Approved"
                elif tracker=="growth_tracker":
                    col="Project Status"
                    val="Completed"
                elif tracker=="ve_tracker":
                    col="Status"
                    val="Completed"
                cur.execute("""select count(project_id) AS comp_count
                    from projects p join status s
                    on p.id=s.project_id
                    where s.column_name=%s and s.current_value=%s
                    and s.completion_date>=CURRENT_DATE - INTERVAL '7days'"""
                ,(col,val))
                row =cur.fetchone()
                count=row["comp_count"]
                return {"status":"success","count":count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database execution trace failure: {str(e)}")
                
                


