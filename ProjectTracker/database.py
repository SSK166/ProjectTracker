import sqlite3
import pandas as pd

DB_PATH = "projects.db"

STATUS_COLUMNS = [
    "KLD Status",
    "Artwork Status",
    "Artwork to Vendor Status",
    "Artwork to Vendor Status 2",
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

def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            packaging_type TEXT,
            packaging_option TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            column_name TEXT,
            deadline DATE,
            UNIQUE(project_id, column_name),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    conn.commit()
    conn.close()

def import_from_excel():
    """Import from the original Excel file (one-time setup)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    df = pd.read_excel(EXCEL_PATH, sheet_name="Project Tracker")
    df = df.rename(columns={
        "Code creation ": "Code creation"
    })
    df["Code creation"] = df["Code creation"].apply(
        lambda x: str(int(x)) if pd.notna(x) else None
    )
    df["Project"] = df["Project"].ffill()

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO projects (project_name, packaging_type, packaging_option)
            VALUES (?, ?, ?)
        """, (row["Project"], row["Packaging Type"], row["Packaging Option"]))

        project_id = cursor.lastrowid
        for col in STATUS_COLUMNS:
            value = row.get(col, None)
            cursor.execute("""
                INSERT INTO status (project_id, column_name, current_value)
                VALUES (?, ?, ?)
            """, (project_id, col, str(value) if pd.notna(value) else None))

    conn.commit()
    conn.close()
    print("Data imported successfully")

if __name__ == "__main__":
    create_tables()
    print("Tables created successfully")

    # Uncomment to seed from original Excel:
    # import_from_excel()

    conn = sqlite3.connect(DB_PATH)
    print("--- PROJECTS ---")
    print(pd.read_sql_query("SELECT * FROM projects LIMIT 10", conn))
    print("--- STATUS ---")
    print(pd.read_sql_query("SELECT * FROM status LIMIT 20", conn))
    conn.close()