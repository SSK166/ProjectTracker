import psycopg2
import psycopg2.extras
# import pandas as pd
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

class User:
    def __init__(self,name:str,pw:str,role:str,id:int=None):
        self.id=id
        self.name=name
        self.pw=pw
        self.role=role

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
    
    def get_conn(self):
        conn = psycopg2.connect(**self.db_params)#unpacking
        # This forces every cursor spawned by this connection to be a RealDictCursor automatically
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn


    def create_auth_table(self):
        #creating tables
        with self.get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS auth (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        role VARCHAR(40) NOT NULL
                    )
                """)
                conn.commit()
    
    def create_session_table(self):
        with self.get_conn() as conn:
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
    
    def create_session(self,user_id:int,session_id:str,expires_at:datetime) -> bool:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                
                cur.execute("""
                    INSERT INTO sessions(session_id,user_id,expires_at)
                    VALUES(%s, %s, %s)
                """,(session_id,user_id,expires_at))
                conn.commit()
                return True
    
    def get_user_by_session(self,session_id:int) -> User:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT u.* FROM
                    auth u JOIN sessions s
                    ON s.user_id=u.id
                    WHERE s.session_id = %s and s.expires_at > %s
                """,(session_id,datetime.now()))
                row=cur.fetchone()
                if row is None:
                    return None
                return User(row["username"],row["password"],row["role"],row["id"])
    
    def delete_session(self,session_id:int)->bool:
        with self.get_conn() as conn:
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
    
    def create_user(self,user:User):
        #user creation for register
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO auth(username,password,role)
                    VALUES (%s,%s,%s)
                """,(user.name,user.pw,user.role))
                conn.commit()
    
    def get_by_username(self,name:str):
        with self.get_conn() as conn:
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
                        row["id"]
                    )
                else:
                    return None

    def get_all_users(self):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM auth
                """)
                rows=cur.fetchall()
                return [User(row["username"],
                        row["password"],
                        row["role"],
                        row["id"]) for row in rows]
    
    def switch_role(self,user_id:int,new_role:str) -> bool:
        with self.get_conn() as conn:
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
    
    def delete_user(self,user_id:int) -> bool:
        with self.get_conn() as conn:
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
