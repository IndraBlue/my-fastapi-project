from fastapi import Body, FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

import json
import os


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify ["http://localhost:3000"] for React, etc.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DATA_PATH = "src/data/demo1.json"


class EMPLOYEE_BASE(BaseModel):
    id:int
    name:str
    age:int
    role:str

def load_data():
    """Load data from JSON file with error handling."""
    try:
        # Check if file exists
        if not os.path.exists(DATA_PATH):
            return JSONResponse(
                status_code=404,
                content={"error": f"File '{DATA_PATH}' not found"}
            )

        # Try reading and parsing the JSON
        with open(DATA_PATH, "r") as file:
            data = json.load(file)

        # Validate data type
        if not isinstance(data, list):
            return JSONResponse(
                status_code=400,
                content={"error": "JSON file does not contain a list of employees"}
            )

        return data

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
    """Fetch and filter employees with error handling."""
    data = load_data()

    # If load_data() returned a JSONResponse (error), just return it directly
    if isinstance(data, JSONResponse):
        return data

    try:
        # Filter by role
        if role:
            data = [emp for emp in data if emp.get("role", "").lower() == role.lower()]

        # Filter by minimum age
        if min_age is not None:
            data = [emp for emp in data if emp.get("age", 0) >= min_age]

        return {"total": len(data), "employees": data}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error filtering data: {str(e)}"}
        )
    
@app.post("/addEmployees")
def add_employee(employee: EMPLOYEE_BASE = Body(...)):
    """Add a new employee to the JSON file."""
    data = load_data()
    if isinstance(data, JSONResponse):
        return data

    try:
        data.append(employee.model_dump())

        with open(DATA_PATH, "w") as file:
            json.dump(data, file, indent=2)

        return {"message": "Employee added successfully", "employee": employee}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error saving employee: {str(e)}"}
        )

@app.delete("/removeEmployees")
def delete_employee(name: str = Query(...)):
    """Delete an employee by name."""
    data = load_data()
    if isinstance(data, JSONResponse):
        return data

    try:
        original_count = len(data)
        data = [emp for emp in data if emp.get("name", "").lower() != name.lower()]
        if len(data) == original_count:
            return JSONResponse(
                status_code=404,
                content={"error": f"No employee found with name '{name}'"}
            )

        with open(DATA_PATH, "w") as file:
            json.dump(data, file, indent=2)

        return {"message": f"Employee '{name}' deleted successfully", "remaining": len(data)}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error deleting employee: {str(e)}"}
        )
