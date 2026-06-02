# to avoid the circular dependencies
from fastapi import Request, HTTPException, Depends
from typing import List
from userdb import User, UserDB

db = UserDB()

def get_current_user(request: Request) -> User:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="No current session. Log in first"
        )
    cur_user = db.get_user_by_session(session_id=session_id)
    if not cur_user:
        raise HTTPException(
            status_code=401,
            detail="No user logged in. Log in first"
        )
    return cur_user

def verify_roles(approved_roles: List[str]):
    def dependency(current_user: User = Depends(get_current_user)):
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