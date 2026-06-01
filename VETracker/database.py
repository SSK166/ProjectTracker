import psycopg2
import psycopg2.extras
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

STATUS_COLUMNS = [
    "Development",
    "KLD",
    "Artwork",
    "Trial",
    "Implementation",
    "Comments",
    "Status"
]

EXCEL_PATH = r"D:\internship2026\ProjectTracker\VETracker\VE Projects.xlsx"

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
            packaging_option TEXT,
            pm_code INT,
            vendor TEXT,
            eta DATE       
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

    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1",header=1)
    print(f"Columns : {df.columns}")

    df = df.rename(columns={"Description":"Project","PM code": "PM Code","KLD ":"KLD"})
    print(f"Columns : {df.columns}")
    df["PM Code"] = df["PM Code"].apply(
        lambda x: str(int(x)) if pd.notna(x) else None
    )
    df["ETA"] = pd.to_datetime(df["ETA"], errors='coerce')

    for _, row in df.iterrows():
        # RETURNING id replaces lastrowid
        eta_val = row["ETA"].to_pydatetime().date() if pd.notna(row["ETA"]) else None
        pm_code = row.get("PM Code")
        project_desc = row.get("Project")
        composite_name = f"PM - {pm_code} - {project_desc}" if pm_code and project_desc else project_desc

        cursor.execute("""
            INSERT INTO projects (project_name, packaging_type, packaging_option,vendor,pm_code,eta)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (composite_name, row["Packaging Type"], row["Packaging Option"],row["Vendor"],row["PM Code"],eta_val))

        project_id = cursor.fetchone()[0]

        for col in STATUS_COLUMNS:
            value = row.get(col, None)
            cursor.execute("""
                INSERT INTO status (project_id, column_name, current_value)
                VALUES (%s, %s, %s)
            """, (project_id, col, str(value).title() if pd.notna(value) else None))

    conn.commit()
    cursor.close()
    conn.close()
    print("Data imported successfully")

if __name__ == "__main__":
    create_tables()
    # Uncomment to seed from original Excel:
    import_from_excel()