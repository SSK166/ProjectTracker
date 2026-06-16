# to avoid the circular dependencies
from fastapi import Request, HTTPException, Depends
from typing import List
from userdb import User, UserDB
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta, timezone


db = UserDB()

from fastapi import HTTPException
from starlette.responses import RedirectResponse

def get_current_user(request: Request) -> User:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=307,
            headers={"Location": "/?msg=No+session+Please+log+in"}
        )
    cur_user = db.get_user_by_session(session_id=session_id)
    if not cur_user:
        raise HTTPException(
            status_code=307,
            headers={"Location": "/?msg=No+user+logged+in"}
        )
    return cur_user

def verify_roles(approved_roles: List[str]):
    def dependency(current_user: User = Depends(get_current_user)):
        if not current_user:
            raise HTTPException(
                status_code=307,
                headers={"Location": "/?msg=No+user+logged+in"}
            )
        if current_user.role not in approved_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action"
            )
        return current_user
    return dependency

IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    return datetime.now(IST)
def get_ist_date():
    return datetime.now(IST).date()