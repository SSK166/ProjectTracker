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

from dependencies import get_current_user,verify_roles, get_ist_now, get_ist_date
from userdb import User,UserDB

router=APIRouter()
db=UserDB()

from psycopg2 import pool as pg_pool

_pools = {}

def _get_pool(tracker: str):
    if tracker not in _pools:
        if tracker == "project_tracker":
            db_name = "PROJECT_DB_NAME"
        elif tracker == "growth_tracker":
            db_name = "GROWTH_DB_NAME"
        elif tracker == "ve_tracker":
            db_name = "VALUE_DB_NAME"
        else:
            raise HTTPException(status_code=400, detail="No such database found")
        _pools[tracker] = pg_pool.ThreadedConnectionPool(
            minconn=1, maxconn=5,
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dbname=os.getenv(db_name),
        )
    return _pools[tracker]

def get_conn(tracker: str):
    return _get_pool(tracker).getconn()

@router.get("/summary")
def get_central_summary(current_user: User = Depends(verify_roles(["admin"]))):
    today = get_ist_date().isoformat()
    summary_data = {
        "status": "success",
        "timestamp": get_ist_now().isoformat(),
        "trackers": {}
    }
    
    # --- SCANNING PROJECT TRACKER ---
    conn = None
    try:
        conn=get_conn("project_tracker")
        with conn.cursor() as cur:            
            cur.execute("SELECT COUNT(*) FROM projects")
            t1_total = cur.fetchone()[0]
            cur.execute("""
                SELECT COUNT(*) FROM deadlines d
                JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                WHERE d.deadline < %s
                AND (s.current_value IS NULL OR s.current_value NOT IN('Approved','Closed','Dispatched','Yes','Received'))
            """, (today,))
            t1_alerts = cur.fetchone()[0]
            cur.execute("""
                SELECT COUNT(*) FROM deadlines d
                JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                WHERE d.deadline = %s
                AND (s.current_value IS NULL OR s.current_value NOT IN ('Approved','Closed','Dispatched','Yes','Received'))
            """, (today,))
            t1_due_today = cur.fetchone()[0]
            cur.execute("""
                SELECT count(*) FROM status 
                WHERE completion_date = %s
            """,(today,))
            t1_completed_today=cur.fetchone()[0]
            cur.execute("""
                SELECT count(p.id) 
                FROM projects p JOIN status s
                ON p.id=s.project_id
                WHERE s.column_name='Project Status' AND LOWER(TRIM(s.current_value))='approved'
            """)
            t1_completed=cur.fetchone()[0]
        summary_data["trackers"]["project_tracker"] = {"name": "Project Tracker", "total": t1_total, "alerts": t1_alerts, "due_today":t1_due_today,"completed_today":t1_completed_today,"completed":t1_completed}
    except Exception as e:
        summary_data["trackers"]["project_tracker"] = {"error": f"Database offline: {str(e)}"}
    finally:
        if conn:
            _get_pool("project_tracker").putconn(conn)

    # --- SCANNING GROWTH TRACKER ---
    conn = None
    try:
        conn = get_conn("growth_tracker")
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM projects")
            t3_total = cur.fetchone()[0]
            cur.execute("""
                SELECT COUNT(*)
                FROM deadlines d
                JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                WHERE d.deadline < %s
                AND (s.current_value IS NULL OR s.current_value NOT IN ('Received', 'Connected', 'Completed', 'KLD Shared'))
            """, (today,))
            t3_alerts = cur.fetchone()[0]
            cur.execute("""
                SELECT COUNT(*)
                FROM deadlines d
                JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                WHERE d.deadline = %s
                AND (s.current_value IS NULL OR s.current_value NOT IN ('Received', 'Connected', 'Completed', 'KLD Shared'))
            """, (today,))
            t3_due_today = cur.fetchone()[0]
            cur.execute("""
                SELECT count(*) FROM status 
                WHERE completion_date = %s
            """,(today,))
            t3_completed_today=cur.fetchone()[0]
            cur.execute("""
                SELECT count(p.id) 
                FROM projects p JOIN status s
                ON p.id=s.project_id
                WHERE s.column_name='Project Status' AND LOWER(TRIM(s.current_value))='completed'
            """)
            t3_completed=cur.fetchone()[0]
        summary_data["trackers"]["growth_tracker"] = {"name": "Growth Tracker", "total": t3_total, "alerts": t3_alerts, "due_today":t3_due_today,"completed_today":t3_completed_today,"completed":t3_completed}
    except Exception as e:
        summary_data["trackers"]["growth_tracker"] = {"error": f"Database offline: {str(e)}"}
    finally:
        if conn:
            _get_pool("growth_tracker").putconn(conn)

    # --- SCANNING VALUE ENGINEERING TRACKER ---
    conn = None
    try:
        conn=get_conn("ve_tracker")
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM projects")
            t4_total = cur.fetchone()[0]
            cur.execute("""
                SELECT COUNT(*) FROM deadlines d
                JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                WHERE d.deadline < %s
                AND (s.current_value IS NULL OR s.current_value NOT IN ('Completed','Shared'))
            """, (today,))
            t4_alerts = cur.fetchone()[0]
            cur.execute("""
                SELECT COUNT(*) FROM deadlines d
                JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                WHERE d.deadline = %s
                AND (s.current_value IS NULL OR s.current_value NOT IN ('Completed','Shared'))
            """, (today,))
            t4_due_today = cur.fetchone()[0]
            cur.execute("""
                SELECT count(*) FROM status 
                WHERE completion_date = %s
            """,(today,))
            t4_completed_today=cur.fetchone()[0]
            cur.execute("""
                SELECT count(p.id) 
                FROM projects p JOIN status s
                ON p.id=s.project_id
                WHERE s.column_name='Status' AND LOWER(TRIM(s.current_value))='completed'
            """)
            t4_completed=cur.fetchone()[0]
        summary_data["trackers"]["ve_tracker"] = {"name": "Value Engineering Tracker", "total": t4_total, "alerts": t4_alerts, "due_today":t4_due_today,"completed_today":t4_completed_today,"completed":t4_completed}
    except Exception as e:
        summary_data["trackers"]["ve_tracker"] = {"error": f"Database offline: {str(e)}"}
    finally:
        if conn:
            _get_pool("ve_tracker").putconn(conn)

    return summary_data

@router.put("/role")
def update_role(username:str=Form(...),role:str=Form(...),current_user:User=Depends(verify_roles(["admin"]))):
    existing_user=db.get_by_username(username)
    if not existing_user:
        raise HTTPException(
            status_code=404,
            detail="No user found. Enter the right username"
        )
    if existing_user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot change your own role"
        )
    switch=db.switch_role(existing_user.id,role)
    if not switch:
        raise HTTPException(
            status_code=500,
            detail="Server Error Role could not be updated"
        )
    return {"status":"success","message":f"User role updated to {role}"}

@router.delete("/user")
def delete_user(username:str=Form(...),current_user:User=Depends(verify_roles(["admin"]))):
    existing_user=db.get_by_username(username)
    if not existing_user:
        raise HTTPException(
            status_code=404,
            detail="No such user exists"
        )
    if existing_user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot delete your own account"
        )
    dlt = db.delete_user(existing_user.id)
    if not dlt:
        raise HTTPException(
            status_code=500,
            detail="Server Error. User could not be deleted"
        )
    return {"status":"success","message":"User deleted"}


@router.get("/upcoming/{tracker}")
def get_upcoming_deadlines(tracker:str,current_user: User = Depends(verify_roles(["admin"]))):
    conn = None # to prevent NameError risk 
    try:
        conn=get_conn(tracker)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT p.project_name, d.column_name, s.current_value, d.deadline 
                FROM deadlines d
                JOIN projects p ON p.id = d.project_id
                JOIN status s ON s.project_id = d.project_id AND s.column_name = d.column_name
                WHERE d.deadline > %s 
                    AND d.deadline <= %s + INTERVAL '7 days'
                    AND s.current_value NOT IN ('Approved','Closed','Dispatched','Completed','Shared','Received','Yes')
                ORDER BY d.deadline ASC
            """,(get_ist_date(),get_ist_date()))
            rows = cur.fetchall()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database execution trace failure: {str(e)}")
    finally:
        if conn:
            _get_pool(tracker).putconn(conn)
                
@router.get('/last-7-days-complete-projects/{tracker}')
def get_projects_completed_in_last_7_days(tracker:str,current_user:User=Depends(verify_roles(["admin"]))):
    conn = None
    try:
        conn=get_conn(tracker)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if tracker=="project_tracker":
                col="Project Status"
                val="Approved"
            elif tracker=="growth_tracker":
                col="Project Status"
                val="Completed"
            elif tracker=="ve_tracker":
                col="Status"
                val="Completed"
            else:
                raise HTTPException(
                    status_code=400,
                    detail="No such database found"
                )
            cur.execute("""select p.id,p.project_name,s.column_name,s.completion_date AS comp_date
                from projects p join status s
                on p.id=s.project_id
                where s.column_name=%s and s.current_value=%s
                and s.completion_date >= NOW() - INTERVAL '7 days'"""
            ,(col,val))
            rows =cur.fetchall()
            return {"status":"success","tasks":rows}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database execution trace failure: {str(e)}")
    finally:
        if conn:
            _get_pool(tracker).putconn(conn)

@router.get('/today-complete-tasks/{tracker}')
def get_tasks_completed_today(tracker:str,current_user:User=Depends(verify_roles(["admin"]))):
    conn = None
    try:
        conn=get_conn(tracker)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT p.id,p.project_name,s.column_name,s.current_value
                FROM status s join projects p
                ON p.id=s.project_id
                WHERE completion_date = %s"""
            ,(get_ist_date().isoformat(),))
            rows =cur.fetchall()
            return {"status":"success","tasks":rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database execution trace failure: {str(e)}")
    finally:
        if conn:
            _get_pool(tracker).putconn(conn)


@router.get('/all-users')
def get_users(current_user:User=Depends(verify_roles(["admin"]))):
    users = db.get_all_users()
    if users:
        return {'status':'success','users':users}
    else:
        raise HTTPException(
            status_code=500,
            detail="Server Error No users found"
        )