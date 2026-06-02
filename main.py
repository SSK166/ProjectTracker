import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, Response, Request, HTTPException, Depends, status, Form
from fastapi.responses import RedirectResponse
import bcrypt
from typing import List
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

#Import from userdb

from userdb import User,UserDB


from ProjectTracker.projectMain import router as project_router
from GrowthTracker.growthMain import router as growth_router
from VETracker.valueMain import router as value_router

app = FastAPI()

app.mount("/track/static", StaticFiles(directory="ProjectTracker/static"), name="track_static")
app.mount("/growth/static", StaticFiles(directory="GrowthTracker/static"), name="growth_static")
app.mount("/value/static", StaticFiles(directory="VETracker/static"), name="value_static")

db = UserDB()

templates = Jinja2Templates(directory=".")



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
    response.set_cookie(key="session_id",
                        value=session_id,
                        httponly=True,
                        samesite='lax')
    return {"status":"success",
    "message":"User logged in successfully"}

def get_current_user(request:Request) -> User:
    session_id=request.cookies.get("session_id") #retrieving session_id from cookie
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="No current session. Log in first"
        )
    cur_user=db.get_user_by_session(session_id=session_id) #Retrieving the current user details
    if not cur_user:
        raise HTTPException(
            status_code=401,
            detail="No user logged in. Log in first"
        )
    return cur_user

@app.get("/track", response_class=HTMLResponse)
def serve_project_tracker_ui(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(name="ProjectTracker/templates/index.html", context={"request": request})

@app.get("/growth", response_class=HTMLResponse)
def serve_growth_tracker_ui(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(name="GrowthTracker/templates/index.html", context={"request": request})

@app.get("/value", response_class=HTMLResponse)
def serve_ve_tracker_ui(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(name="VETracker/templates/index.html", context={"request": request})

@app.get("/auth/protected")
def cur_uname(current_user:User=Depends(get_current_user)):
    return {"status":"success","message":f"Current user is {current_user.name}","role":current_user.role}

def verify_roles(approved_roles:List[str]):
    def dependency(current_user:User=Depends(get_current_user)):
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="No user found. Log in first"
            )
        if current_user.role not in approved_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action"
            )
        return current_user
    return dependency

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

app.include_router(project_router, prefix="/track", tags=["Project Data Feed"])
app.include_router(growth_router, prefix="/growth", tags=["Growth Data Feed"])
app.include_router(value_router, prefix="/value", tags=["Value Engineering Data Feed"])