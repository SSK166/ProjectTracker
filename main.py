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

#Import from userdb
from dependencies import get_current_user,verify_roles
from userdb import User,UserDB


from ProjectTracker.projectMain import router as project_router
from GrowthTracker.growthMain import router as growth_router
from VETracker.valueMain import router as value_router
from adminPanel.adminMain import router as admin_router

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173","http://localhost:5173"], # Your local React development environment URL
    allow_credentials=True,                 # 🚨 CRITICAL: Allows browser session cookies to pass through the security wall!
    allow_methods=["*"],
    allow_headers=["*"],
)
# In main.py

db = UserDB()

templates = Jinja2Templates(directory=".")

@app.get("/", response_class=HTMLResponse)
def serve_authentication_portal(request: Request):
    # Pass request directly as a primary keyword argument
    return templates.TemplateResponse(request=request, name="landing/templates/auth.html")


@app.on_event("startup") 
def manage_startup():
    db.create_auth_table()
    db.create_session_table()

def hash_password(password:str) -> str:
    #returns a hased password for the given password
    salt=bcrypt.gensalt()
    hashed=bcrypt.hashpw(password.encode('utf-8'),salt=salt)
    return hashed.decode('utf-8')

#checkpw has strict input order plain first hashed next
def verify_password(hash_pw:str,pw:str) -> bool:
    return bcrypt.checkpw(pw.encode('utf-8'),hash_pw.encode('utf-8'))

@app.post("/auth/register")
def register(username:str=Form(...),password:str=Form(...)):
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
    new_user=User(username,hashed_pw,"user")
    db.create_user(new_user)
    return {"status": "success", "message": "Account created successfully!"}

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
    db.create_session(existing_user.id,session_id,expires_at=datetime.now()+timedelta(days=7))
    # print(f"User {existing_user.name} Role {existing_user.role}")
    response.set_cookie(key="session_id",
                        value=session_id,
                        httponly=True,
                        samesite='none',
                        secure=True)
    return {"status":"success",
    "message":"User logged in successfully"}

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
    response.delete_cookie(key="session_id")
    return {"status":"success","message":"User logged out successfully"}

@app.get("/auth/protected")
def get_user_role(current_user:User=Depends(get_current_user)):    
    return {
        "status":"success",
        "role":current_user.role,
        "username":current_user.name
    }   

app.include_router(admin_router,prefix="/admin",tags=["AdminPage"],dependencies=[Depends(verify_roles(["admin"]))])
app.include_router(project_router, prefix="/track", tags=["Project Data Feed"],dependencies=[Depends(get_current_user)])
app.include_router(growth_router, prefix="/growth", tags=["Growth Data Feed"],dependencies=[Depends(get_current_user)])
app.include_router(value_router, prefix="/value", tags=["Value Engineering Data Feed"],dependencies=[Depends(get_current_user)])

#Mount static resources
app.mount("/admin/assets", StaticFiles(directory="adminPanel/admin-frontend/dist/assets"), name="admin_assets")
app.mount("/landing/static", StaticFiles(directory="landing/static"), name="landing_static")
app.mount("/track/static", StaticFiles(directory="ProjectTracker/static"), name="track_static")
app.mount("/growth/static", StaticFiles(directory="GrowthTracker/static"), name="growth_static")
app.mount("/value/static", StaticFiles(directory="VETracker/static"), name="value_static")