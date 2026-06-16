import psycopg2
import psycopg2.extras
# import pandas as pd
from dotenv import load_dotenv
import os
from psycopg2 import pool
from datetime import datetime, timedelta, timezone

load_dotenv()

class User:
    def __init__(self,name:str,pw:str,role:str,id:int=None,email:str=None):
        self.id=id
        self.name=name
        self.pw=pw
        self.role=role
        self.email=email

class ResetRequest:
    def __init__(self,username:str,password:str):
        self.name=username
        self.pw=password

class UserDB:
    def __init__(self):
        #creating a params object that I can use it to create new connections easily
        self.db_params={
            "host":os.getenv('DB_HOST'),
            "port":os.getenv('DB_PORT'),
            "dbname":os.getenv('USER_DB_NAME'),
            "user":os.getenv('DB_USER'),
            "password":os.getenv('DB_PASSWORD')
        }
        self.pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            **self.db_params
        )
    
    def get_conn(self):
        conn = self.pool.getconn()#unpacking
        # This forces every cursor spawned by this connection to be a RealDictCursor automatically
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn

    def create_otp_table(self):
        conn = self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS otp_requests (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER UNIQUE NOT NULL,       -- UNIQUE so one active OTP per user
                        otp_hash TEXT NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        used BOOLEAN DEFAULT false,
                        FOREIGN KEY(user_id) REFERENCES auth(id) ON DELETE CASCADE
                    )
                """)
                conn.commit()
        finally:
            if conn:
                self.pool.putconn(conn)

    def create_auth_table(self):
        #creating tables
        conn=self.get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS auth (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        role VARCHAR(40) NOT NULL
                    )
                """)
                conn.commit()
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def create_session_table(self):
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS sessions(
                        session_id VARCHAR(255) PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES auth(id) ON DELETE CASCADE
                    )
                """)
            conn.commit()
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def create_session(self,user_id:int,session_id:str,expires_at:datetime) -> bool:
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sessions(session_id,user_id,expires_at)
                    VALUES(%s, %s, %s)
                """,(session_id,user_id,expires_at))
                conn.commit()
                return True
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def get_user_by_session(self,session_id:int) -> User:
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT u.* FROM
                    auth u JOIN sessions s
                    ON s.user_id=u.id
                    WHERE s.session_id = %s and s.expires_at > %s
                """,(session_id,get_ist_now()))
                row=cur.fetchone()
                if row is None:
                    return None
                return User(row["username"],row["password"],row["role"],row["id"],row["email"])
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def delete_session(self,session_id:int)->bool:
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM sessions where session_id=%s
                """,(session_id,))
                row=cur.fetchone()
                if row is None:
                    return False
                cur.execute("""
                    DELETE FROM sessions where session_id=%s
                """,(session_id,))
                conn.commit()
                return True
        finally:
            if conn:
                self.pool.putconn(conn)

    def create_user(self,user:User):
        #user creation for register
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO auth(username,password,role,email)
                    VALUES (%s,%s,%s,%s)
                """,(user.name,user.pw,user.role,user.email))
                conn.commit()
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def get_by_username(self,name:str):
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM auth 
                    WHERE username = %s
                """,(name,))
                row=cur.fetchone()
                if row is not None:
                    return User(
                        row["username"],
                        row["password"],
                        row["role"],
                        row["id"],
                        row["email"]
                    )
                else:
                    return None
        finally:
            if conn:
                self.pool.putconn(conn)

    def get_all_users(self):
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM auth
                """)
                rows=cur.fetchall()
                return [User(row["username"],
                        row["password"],
                        row["role"],
                        row["id"],
                        row["email"]) for row in rows]
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def switch_role(self,user_id:int,new_role:str) -> bool:
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM auth WHERE id=%s
                """,(user_id,))
                row=cur.fetchone()
                if(row is None):
                   return False
                cur.execute("""
                    UPDATE auth SET role=%s WHERE id=%s 
                """,(new_role,user_id))
                conn.commit()
                return True
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def delete_user(self,user_id:int) -> bool:
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM auth WHERE id=%s
                """,(user_id,))
                row=cur.fetchone()
                if(row is None):
                   return False
                cur.execute("""
                    DELETE FROM auth WHERE id=%s 
                """,(user_id,))
                conn.commit()
                return True
        finally:
            if conn:
                self.pool.putconn(conn)

    def get_by_email(self,email:str)->User:
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM auth 
                    WHERE email = %s
                """,(email,))
                row = cur.fetchone()
                if row is not None:
                    return User(row["username"],
                        row["password"],
                        row["role"],
                        row["id"],
                        row["email"])
                else:
                    return None
        finally:
            if conn:
                self.pool.putconn(conn)

    def reset_password(self,user_id:int,hashed_pw:str):
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE auth SET password = %s WHERE id=%s
                """,(hashed_pw,user_id,))
                conn.commit()
        finally:
            if conn:
                self.pool.putconn(conn)
                
    def store_otp(self, user_id: int, otp_hash: str, expires_at):
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO otp_requests(user_id, otp_hash, expires_at, used)
                    VALUES (%s, %s, %s, false)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        otp_hash = EXCLUDED.otp_hash,
                        expires_at = EXCLUDED.expires_at,
                        used = false
                """, (user_id, otp_hash, expires_at))
                conn.commit()
        finally:
            if conn:
                self.pool.putconn(conn)

    def get_otp(self, user_id: int):
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM otp_requests 
                    WHERE user_id = %s AND used = false AND expires_at > %s
                """, (user_id, get_ist_now()))
                return cur.fetchone()
        finally:
            if conn:
                self.pool.putconn(conn)

    def mark_otp_used(self, user_id: int):
        conn=self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE otp_requests SET used = true WHERE user_id = %s", (user_id,))
                conn.commit()
        finally:
            if conn:
                self.pool.putconn(conn)
        
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    return datetime.now(IST)
def get_ist_date():
    return datetime.now(IST).date()