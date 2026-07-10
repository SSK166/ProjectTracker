# Enterprise Workflow & Project Tracking System

## Overview

This repository contains the source code for a comprehensive, multi-tracker management system designed to digitize, monitor, and optimize complex business workflows. Initially developed to handle packaging project lifecycles and growth pipelines, the architecture is scalable to any operational workflow requiring strict data integrity, role-based access control, and automated deadline tracking.

The system is divided into isolated tracking environments (Regular Projects, Growth Pipeline, and Value Engineering) overseen by a centralized Administrative Dashboard.

## System Architecture

The application follows a decoupled client-server architecture, utilizing a RESTful API for communication between the React frontend and the Python/FastAPI backend.

```text
+-----------------------+         HTTPS / REST          +-----------------------+
|                       |  (Cookie-based Sessions)      |                       |
|   React Client (UI)   | <---------------------------> |    FastAPI Backend    |
|   (Vite, JS, CSS)     |                               |    (Python, Uvicorn)  |
|                       |                               |                       |
+-----------------------+                               +-----------------------+
                                                               |        |
                                         psycopg2 Threaded     |        | SMTP 
                                         Connection Pooling    |        | (TLS 587)
                                                               V        V
                                        +----------------------+   +------------------+
                                        |  PostgreSQL Cluster  |   |    Brevo API     |
                                        |  (Multiple DBs)      |   | (Email Services) |
                                        +----------------------+   +------------------+

```

## Core Features

* **Timezone-Resilient Architecture:** All date and time logic is strictly anchored to Indian Standard Time (IST) at the application layer. This eliminates deployment risks associated with server-local time configurations (UTC environments), ensuring flawless deadline calculations across all global deployments.
* **Role-Based Access Control (RBAC):** Granular, middleware-enforced security routing. Access is segmented into Standard Users, Tiered Managers, and Administrators, with strict validation on all mutating (PUT/POST/DELETE) requests.
* **Database Connection Pooling:** Implements `psycopg2.pool.ThreadedConnectionPool` to manage concurrent database interactions safely, preventing connection exhaustion under heavy load.
* **Atomic Database Operations:** Utilizes PostgreSQL `ON CONFLICT DO UPDATE` constraints to guarantee data consistency during high-frequency status updates or network retries.
* **Automated Analytics & Reporting:** The centralized Admin Panel aggregates cross-tracker data in real-time, calculating overall system health, overdue backlogs, and daily completion metrics.
* **Data Ingestion & Export:** Seamless integration with legacy business processes via Pandas and OpenPyXL, allowing for bulk Excel imports and formatted spreadsheet generation.

## Technology Stack

**Backend:**

* Python 3.x
* FastAPI (Web Framework)
* PostgreSQL (Database)
* psycopg2-binary (Database Adapter)
* Pandas & OpenPyXL (Data Processing)
* smtplib (Brevo SMTP Integration)

**Frontend:**

* React.js (Component-based UI)
* Vite (Build Tool)
* Native CSS (Styling)

## Local Development Setup

### Prerequisites

* Python 3.9+
* Node.js v16+
* PostgreSQL server running locally or accessible via network.

### 1. Backend Configuration

Navigate to the backend directory and install the required dependencies:

```bash
pip install -r requirements.txt

```

Create a `.env` file in the root backend directory. This file must not be committed to version control:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# Tracker Databases
PROJECT_DB_NAME=project_tracker
GROWTH_DB_NAME=growth_tracker
VALUE_DB_NAME=value_tracker

# External Services
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=your_brevo_email
SMTP_PASS=your_brevo_smtp_key

# Security
SECRET_KEY=your_secure_random_string

```

Run the backend server:

```bash
uvicorn main:app --reload

```

### 2. Frontend Configuration

Navigate to the frontend directory, install dependencies, and start the development server:

```bash
npm install
npm run dev

```

*Note: Ensure all `fetch` URLs in the React codebase are configured for relative paths in production or point to `http://127.0.0.1:8000` for local development.*

## Production Deployment Notes

This application is designed to be deployed on modern cloud Platforms as a Service (PaaS) such as Railway, Render, or Heroku.

1. **Environment Variables:** All `.env` configurations must be migrated to the deployment provider's environment variable dashboard.
2. **CORS Middleware:** Ensure `main.py` is configured with `CORSMiddleware` to accept cross-origin requests exclusively from your production frontend domain.
3. **Process Management:** Use a production-grade ASGI server configuration (e.g., Gunicorn with Uvicorn workers) defined in a `Procfile`.
