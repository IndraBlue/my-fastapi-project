import json
import sqlite3
import os
from fastapi import FastAPI, Body, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
app = FastAPI()

# 1. Update your DB Path to match your file name
DB_PATH = r"C:\Users\indra\myDB.db" 


from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

load_dotenv()




def get_db_connection():
    print(f"Connecting to database at: {os.path.abspath(DB_PATH)}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    return conn

# --- FASTMAIL CONFIG (Your Original Method) ---
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,   # Must be True for Port 587
    MAIL_SSL_TLS=False,   # Must be False when using STARTTLS/587
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify ["http://localhost:3000"] for React, etc.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
LOGIN_DATA="src/data/users.json"
class EMPLOYEE_BASE(BaseModel):
    id: str  
    name: str
    age: int
    role: str
    email: str
    m_id:str
    salary:int
    allowances:int
    insurance:int

class LOGIN_BASE(BaseModel):
    userName:str
    password:str

# --- ENDPOINTS ---


# --- THE MAIL FUNCTION (Async as per FastMail requirements) ---
async def send_welcome_email(email_to: str, name: str):
    """Sends email via FastMail SMTP (Gmail)"""
    message = MessageSchema(
        subject="Registration Alert",
        recipients=[email_to],
        body=f"Hello {name}, your profile was created successfully in the system!",
        subtype=MessageType.plain
    )
    fm = FastMail(conf)
    await fm.send_message(message)



@app.get("/debug-db")
def debug_db():
    try:
        # Check if the file actually exists at that path
        if not os.path.exists(DB_PATH):
            return {
                "status": "ERROR",
                "message": "File not found at the path provided",
                "path_searched": DB_PATH
            }

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Look for the table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]
        conn.close()
        
        return {
            "status": "Success",
            "db_path": DB_PATH,
            "file_size_kb": os.path.getsize(DB_PATH) / 1024,
            "tables_found": tables
        }
    except Exception as e:
        return {"status": "Crash", "details": str(e)}
    


def login_data():
    try:
        # Check if file exists
        if not os.path.exists(LOGIN_DATA):
            return JSONResponse(
                status_code=404,
                content={"error": f"File '{LOGIN_DATA}' not found"}
            )

        # Try reading and parsing the JSON
        with open(LOGIN_DATA, "r") as file:
            dataLogin = json.load(file)

        # Validate data type
        if not isinstance(dataLogin, list):
            return JSONResponse(
                status_code=400,
                content={"error": "JSON file does not contain a list of users"}
            )

        return dataLogin

    except json.JSONDecodeError as e:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid JSON format: {str(e)}"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Unexpected error loading JSON: {str(e)}"}
        )
    



@app.get("/employees")
def get_employees(role: str = Query(None), min_age: int = Query(None)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Use double quotes for table names with spaces
    query = 'SELECT * FROM "Details Table" WHERE 1=1'
    params = []
    
    if role:
        query += " AND LOWER(role) = ?"
        params.append(role.lower())
    if min_age is not None:
        query += " AND age >= ?"
        params.append(min_age)
        
    cursor.execute(query, params)
    employees = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"total": len(employees), "employees": employees}



@app.get("/findManager")
def get_Manager(id: str = Query(...)):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    try:
        # Step 1: Manager Query
        query1 = 'SELECT DT.id, DT.name, MT.manager_name FROM "Details Table" AS DT LEFT JOIN "Manager Table" AS MT ON DT.m_id = MT.manager_id WHERE DT.id = ?'
        cursor.execute(query1, (id,))
        manager_row = cursor.fetchone()
        
        if not manager_row:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        result = dict(manager_row)

        # Step 2: Assets Query
        query2 = """
            SELECT AT.assetID, AT.assetModel, AT.assignedName, DT.id, AT.warrantyUpto, 
            (AT.warrantyUpto > DATE('now')) AS warrantyValid  
            FROM "Asset Table" AS AT 
            LEFT JOIN "Details Table" AS DT ON AT.assignedID = DT.id 
            WHERE DT.id = ?
        """
        cursor.execute(query2, (id,))
        asset_rows = cursor.fetchall()

        # --- DEBUG PRINT ---
        print(f"DEBUG: Found {len(asset_rows)} assets for ID {id}")
        for r in asset_rows:
            print(f"DEBUG: Asset Found - {r['assetID']}")
        # -------------------

        result["assets"] = [dict(row) for row in asset_rows]
        return {"mdata": result}

    finally:
        conn.close()

@app.post("/addEmployees")
async def add_employee(background_tasks: BackgroundTasks, employee: EMPLOYEE_BASE = Body(...)):
    """Add employee to SQLite and trigger FastMail background task."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # SQL Insert for "Details Table"
        cursor.execute(
            'INSERT INTO "Details Table" (id, name, age, role, email,m_id) VALUES (?, ?, ?, ?, ?, ?)',
            (employee.id, employee.name, employee.age, employee.role, employee.email, employee.m_id)
        )

        cursor.execute(
            'INSERT INTO "Salary Table" (emp_id,emp_name,basicSalary,allowences,insurance) VALUES (?, ?, ?, ?, ?)',
                       (employee.id,employee.name,employee.salary,employee.allowances, employee.insurance))
        conn.commit()
        
        # Trigger your original FastMail method
        if employee.email:
            background_tasks.add_task(send_welcome_email, employee.email, employee.name)

        return {"message": "Employee added and email queued", "employee": employee}
    
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail=f"Employee ID {employee.id} already exists.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()


@app.put("/editEmployee")
def edit_employee(id: str = Query(...), updated_employee: EMPLOYEE_BASE = Body(...)):
    """
    Edit an existing employee by ID in the SQLite 'Details Table'.
    Note: We use double quotes around "Details Table" because of the space in the name.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # SQL UPDATE statement
        # We update by the 'id' passed in the Query parameter
        cursor.execute(
            'UPDATE "Details Table" SET name=?, age=?, role=?, email=?, m_id=? WHERE id=?',
            (
                updated_employee.name, 
                updated_employee.age, 
                updated_employee.role, 
                updated_employee.email,
                updated_employee.m_id,
                id
            )
        )
        
        conn.commit()
        
        # Check if any row was actually changed
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"No employee found with ID {id}")
            
        return {
            "message": f"Employee {id} updated successfully", 
            "employee": updated_employee
        }
        
    except Exception as e:
        # Catch-all for database errors
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@app.delete("/removeEmployees")
def delete_employee(name: str = Query(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM "Details Table" WHERE LOWER(name) = ?', (name.lower(),))
    conn.commit()
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Employee not found")
        
    conn.close()
    return {"message": f"Deleted {name}"}


@app.post("/login")
def login(request: LOGIN_BASE):
    users = login_data()

    # Find user
    user = next((u for u in users if u["userName"] == request.userName), None)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Compare plain text password
    if user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Return success (or JWT if you want)
    return {"message": "Login successful", "user": request.userName, "picture":user.get("profilePicture")}