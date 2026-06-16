import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, Response, Request, HTTPException, Depends, status, Form
from fastapi.responses import RedirectResponse
import bcrypt
from typing import List
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import date
import requests

#Import from userdb
from dependencies import get_current_user,verify_roles,get_ist_now
from userdb import User,UserDB,ResetRequest

import random
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

from ProjectTracker.projectMain import router as project_router
from GrowthTracker.growthMain import router as growth_router
from VETracker.valueMain import router as value_router
from adminPanel.adminMain import router as admin_router
from GrowthTracker.growthDatabase import create_tables as create_growth_tables
from ProjectTracker.projectDatabase import create_tables as create_project_tables
from VETracker.valueDatabase import create_tables as create_value_tables

from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_auth_table()
    db.create_session_table()
    db.create_otp_table()
    create_growth_tables()
    create_project_tables()
    create_value_tables()
    yield

app = FastAPI(lifespan=lifespan)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://127.0.0.1:5173","http://localhost:5173"], #local React development environment URL
#     allow_credentials=True,                 # Allows browser session cookies to pass through the security wall!
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# In main.py

db = UserDB()

templates = Jinja2Templates(directory=".")

load_dotenv()
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

@app.get("/", response_class=HTMLResponse)
def serve_authentication_portal(request: Request):
    # Pass request directly as a primary keyword argument
    return templates.TemplateResponse(request=request, name="landing/templates/auth.html")

def hash_password(password:str) -> str:
    #returns a hased password for the given password
    salt=bcrypt.gensalt()
    hashed=bcrypt.hashpw(password.encode('utf-8'),salt=salt)
    return hashed.decode('utf-8')

#checkpw has strict input order plain first hashed next
def verify_password(hash_pw:str,pw:str) -> bool:
    return bcrypt.checkpw(pw.encode('utf-8'),hash_pw.encode('utf-8'))

def send_brevo_request(payload):
#Helper to send request to brevo
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": os.getenv("BREVO_API_KEY"),
        "content-type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    
    # Raise an error if the API call fails so your try/except block catches it
    if response.status_code not in [200, 201]:
        raise Exception(f"Brevo API error {response.status_code}: {response.text}")
    return response

def send_otp_email(to_email, otp):
    payload = {
        "sender": {"email": os.getenv("BREVO_SENDER_EMAIL")},
        "to": [{"email": to_email}],
        "subject": "Your Password Reset OTP",
        "textContent": f"Your OTP is: {otp}. This code is valid for 10 minutes."
    }
    send_brevo_request(payload)

def send_inactivity_email(to_email):
    payload = {
        "sender": {"email": os.getenv("BREVO_SENDER_EMAIL")},
        "to": [{"email": to_email}],
        "subject": "Project Tracker - Monthly Activity Ping",
        "textContent": "This is an email sent to you to avoid inactivity. Please ignore this"
    }
    send_brevo_request(payload)

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

@app.post("/auth/register")
def register(username:str=Form(...),password:str=Form(...),email:str=Form(...)):
    if(len(password)>72):
        raise HTTPException(
            status_code=400,
            detail="Password too long. Maximum length of password is 72"
        )
    
    if(len(password)<8):
        raise HTTPException(
            status_code=400,
            detail="Password too short. Password must be at least 8 characters long"
        )
    
    username=username.strip()
    existing_user=db.get_by_username(username)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User with username already exists,Login/Pick another username"
        )
    hashed_pw=hash_password(password)
    new_user=User(username,hashed_pw,"user",email=email)
    db.create_user(new_user)
    return {"status": "success", "message": "Account created successfully!"}

IS_PRODUCTION = os.getenv("ENVIRONMENT") == "production"
@app.post("/auth/login")
def login(response:Response,username:str=Form(...),password:str=Form(...)):
    existing_user=db.get_by_username(username)
    if existing_user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found. Register first"
        )
    
    if not verify_password(existing_user.pw,password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect Username/Password"
        )
    session_id=uuid.uuid4().hex
    db.create_session(existing_user.id,session_id,expires_at=get_ist_now()+timedelta(days=7))
    # print(f"User {existing_user.name} Role {existing_user.role}")
    response.set_cookie(key="session_id",
                        value=session_id,
                        httponly=True,
                        samesite='lax',
                        secure=IS_PRODUCTION)
    return {"status":"success",
    "message":"User logged in successfully"}


@app.get("/auth/forgot-password-page", response_class=HTMLResponse)
def serve_forgot_password_page(request: Request):
    return templates.TemplateResponse(request=request, name="landing/templates/forgot-password.html")

@app.get("/track", response_class=HTMLResponse)
def serve_project_tracker_ui(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request=request, name="ProjectTracker/templates/index.html")

@app.get("/admin", response_class=HTMLResponse)
def serve_admin_panel_ui(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request=request, name="adminPanel/admin-frontend/dist/index.html")

@app.get("/growth", response_class=HTMLResponse)
def serve_growth_tracker_ui(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request=request, name="GrowthTracker/templates/index.html")

@app.get("/value", response_class=HTMLResponse)
def serve_ve_tracker_ui(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request=request, name="VETracker/templates/index.html")


@app.get("/auth/logout")
def logout(request:Request,response:Response):
    session_id=request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=404,
            detail="No user logged in"
        )
    db.delete_session(session_id)
    response.delete_cookie(
        key="session_id",
        path="/",                          
        domain="127.0.0.1",                
        httponly=True,                     
        samesite="lax",
        secure=IS_PRODUCTION                  
    )
    return {"status":"success","message":"User logged out successfully"}

@app.get("/auth/protected")
def get_user_role(current_user:User=Depends(get_current_user)):    
    return {
        "status":"success",
        "role":current_user.role,
        "username":current_user.name
    }   


@app.post("/auth/forgot-password")
def forgot_password(username:str=Form(...),email: str = Form(...)):
    user = db.get_by_email(email.strip().lower())
    if not user:
        return {"status": "success", "message": "If that email exists, an OTP has been sent"}
    if user.name != username:
        return {"status": "success", "message": "If that email exists, an OTP has been sent"}

    otp = generate_otp()
    hashed_otp = hash_password(otp)
    db.store_otp(user.id, hashed_otp, expires_at=get_ist_now() + timedelta(minutes=10))

    try:
        send_otp_email(user.email, otp)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send OTP email")

    return {"status": "success", "message": "If that email exists, an OTP has been sent"}


@app.post("/auth/verify-otp")
def verify_otp(email: str = Form(...), otp: str = Form(...), new_password: str = Form(...) ):
    user = db.get_by_email(email.strip().lower())
    if not user:
        raise HTTPException(status_code=400, detail="Invalid request")

    stored = db.get_otp(user.id)
    if not stored:
        raise HTTPException(status_code=400, detail="OTP expired or invalid")

    if not verify_password(stored["otp_hash"], otp):
        raise HTTPException(status_code=400, detail="Wrong OTP")

    db.mark_otp_used(user.id)

    if len(new_password) < 8 or len(new_password) > 72:
        raise HTTPException(status_code=400, detail="Invalid password length - Password must be at least 8 characters long and at most 72 characters long")

    db.reset_password(user.id, hash_password(new_password))
    return {"status": "success", "role": user.role, "message": "Password reset successfully"}
    
app.include_router(admin_router,prefix="/admin",tags=["AdminPage"],dependencies=[Depends(verify_roles(["admin"]))])
app.include_router(project_router, prefix="/track", tags=["Project Data Feed"],dependencies=[Depends(get_current_user)])
app.include_router(growth_router, prefix="/growth", tags=["Growth Data Feed"],dependencies=[Depends(get_current_user)])
app.include_router(value_router, prefix="/value", tags=["Value Engineering Data Feed"],dependencies=[Depends(get_current_user)])

#Mount static resources
app.mount("/assets", StaticFiles(directory="adminPanel/admin-frontend/dist/assets"), name="admin_assets")
app.mount("/landing/static", StaticFiles(directory="landing/static"), name="landing_static")
app.mount("/track/static", StaticFiles(directory="ProjectTracker/static"), name="track_static")
app.mount("/growth/static", StaticFiles(directory="GrowthTracker/static"), name="growth_static")
app.mount("/value/static", StaticFiles(directory="VETracker/static"), name="value_static")

@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/{catchall:path}", response_class=HTMLResponse)
def serve_admin_panel_ui(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request=request, name="adminPanel/admin-frontend/dist/index.html")