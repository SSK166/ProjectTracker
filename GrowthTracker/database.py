import psycopg2
import psycopg2.extras
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

STATUS_COLUMNS = [
    "KLD Status",
    "Artwork Status",
    "Sampling Status",
    "Commercial Ordering Status",
    "Connectivity Status",
    "Project Status"
]

EXCEL_PATH = r"D:\internship2026\ProjectTracker\GrowthTracker\Project list - Growth.xlsx"

def get_conn():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    return conn

def create_tables():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            project_name TEXT NOT NULL,
            packaging_type TEXT,
            packaging_option TEXT
        )
    """)
    # SERIAL replaces AUTOINCREMENT
    # Everything else is identical

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS status (
            id SERIAL PRIMARY KEY,
            project_id INTEGER,
            column_name TEXT,
            current_value TEXT,
            completion_date DATE,
            UNIQUE(project_id, column_name),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    # UNIQUE constraint uses B-tree indexing on (project_id, column_name).
    # Rows are stored in ascending order of those two columns.
    # We use `for col in STATUS_COLUMNS` on retrieval to preserve
    # the original Excel column order instead of DB sort order.

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deadlines (
            id SERIAL PRIMARY KEY,
            project_id INTEGER,
            column_name TEXT,
            deadline DATE,
            UNIQUE(project_id, column_name),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("Tables created successfully")

def import_from_excel():
    conn = get_conn()
    cursor = conn.cursor()

    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")
    df = df.rename(columns={"Project Description": "Project","KLD ":"KLD Status","Artwork":"Artwork Status","Sampling":"Sampling Status","Commercial ordering":"Commercial Ordering Status","Connectivity":"Connectivity Status","Status":"Project Status"})
    df["Project"] = df["Project"].ffill()

    for _, row in df.iterrows():
        # RETURNING id replaces lastrowid
        cursor.execute("""
            INSERT INTO projects (project_name, packaging_type, packaging_option)
            VALUES (%s, %s, %s) RETURNING id
        """, (row["Project"], row["Packaging Type"], row["Packaging Option"]))

        project_id = cursor.fetchone()[0]

        for col in STATUS_COLUMNS:
            value = row.get(col, None)
            cursor.execute("""
                INSERT INTO status (project_id, column_name, current_value)
                VALUES (%s, %s, %s)
            """, (project_id, col, str(value) if pd.notna(value) else None))

    conn.commit()
    cursor.close()
    conn.close()
    print("Data imported successfully")

if __name__ == "__main__":
    create_tables()
    import_from_excel()  # insert first

    conn = get_conn()
    curs = conn.cursor()
    curs.execute('SELECT * FROM status')
    res = curs.fetchall()
    print(f"Result: {res}")
    curs.close()
    conn.close()