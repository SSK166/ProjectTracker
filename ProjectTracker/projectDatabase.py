import psycopg2
import psycopg2.extras
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

STATUS_COLUMNS = [
    "KLD Status",
    "Artwork Status",
    "Artwork to Vendor Status",
    "Dispatch Status",
    "Cost Closure Status",
    "Project Status",
    "Connectivity Status",
    "PDF Approved",
    "Dimensions",
    "Code creation",
    "Specification",
    "BOM",
    "SOP"
]

EXCEL_PATH = r"D:\internship2026\ProjectTracker\Regular Project_Flow_Tracker.xlsx"

def get_conn():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode= "require" if os.getenv('ENVIRONMENT') else "disable"
    )
    return conn

def create_tables():
    print(f"DEBUG: create_project_tables() is executing against database: '{os.getenv('PROJECT_DB_NAME')}'")
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
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
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
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("Tables created successfully")

def import_from_excel():
    conn = get_conn()
    cursor = conn.cursor()

    df = pd.read_excel(EXCEL_PATH, sheet_name="Project Tracker")
    df = df.rename(columns={"Code creation ": "Code creation"})
    df["Code creation"] = df["Code creation"].apply(
        lambda x: str(int(x)) if pd.notna(x) else None
    )
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
    # Uncomment to seed from original Excel:
    # import_from_excel()