# api.py
import logging
import config # Import config to access APP_DEBUG
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import db_handler
import netsuite_handler
# import mqtt_service # No longer needed as we fetch from DB

# Configure logging based on APP_DEBUG flag
log_level = logging.DEBUG if config.APP_DEBUG else logging.INFO
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
# You might want to get a specific logger instance for more control:
# logger = logging.getLogger(__name__)
# logger.setLevel(log_level)


app = FastAPI()

# Allow all origins for simplicity in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AssignmentPayload(BaseModel):
    machine_id: int
    work_order_id: int
    is_printing_active: bool

class NetSuiteFetchPayload(BaseModel):
    created_at_min: str

@app.get("/api/dashboard-data")
async def get_dashboard_data():
    """Endpoint for the frontend to get all necessary data."""
    assignments_data = await db_handler.get_all_assignments()
    if config.APP_DEBUG:
        print(f"DEBUG: Fetched assignments_data: {assignments_data}")
    assignments_with_summary = []
    for assignment_row in assignments_data:
        assignment = dict(assignment_row) # Ensure it's a mutable dict
        if config.APP_DEBUG:
            print(f"DEBUG: Processing assignment: {assignment}")
        
        default_summary = {
            "total_coils_produced": 0,
            "recent_coil_serial_number": "N/A",
            "recent_coil_quantity": "N/A",
            "total_quantity_made": 0,
            "recent_print_status": "N/A", # Ensure these are part of default
            "recent_error_message": "N/A"
        }
        # Start with default summary, update if WO is assigned
        current_summary = default_summary.copy()

        assigned_wo_no = assignment.get("work_order_no")
        machine_id = assignment.get("machine_id")
        if config.APP_DEBUG:
            print(f"DEBUG: For machine_id {machine_id}, assigned_wo_no is {assigned_wo_no}")

        if assigned_wo_no and machine_id is not None:
            if config.APP_DEBUG:
                print(f"DEBUG: Calling get_production_summary for WO: {assigned_wo_no}, Machine: {machine_id}")
            fetched_summary = await db_handler.get_production_summary_for_assignment(
                work_order_no=assigned_wo_no,
                machine_id=machine_id
            )
            if config.APP_DEBUG:
                print(f"DEBUG: Summary returned from DB: {fetched_summary}")
            current_summary.update(fetched_summary)
        
        assignment.update(current_summary) # Merge summary into the assignment object
        assignments_with_summary.append(assignment)
        
    work_orders = await db_handler.get_available_work_orders()
    return {"assignments": assignments_with_summary, "work_orders": work_orders}

@app.get("/api/mqtt-log")
async def get_mqtt_log():
    """Endpoint to get recent MQTT messages."""
    log_entries = await db_handler.get_recent_raw_mqtt_messages()
    # Format for frontend if needed, or send as is
    # The current frontend expects a list of strings.
    # db_handler.get_recent_raw_mqtt_messages returns a list of dicts.
    formatted_log = [f"{entry['timestamp']} - Topic: {entry['topic']} | Payload: {entry['payload']}" for entry in log_entries]
    return {"log": formatted_log}

@app.post("/api/fetch-netsuite-orders")
async def fetch_netsuite_orders(payload: NetSuiteFetchPayload):
    """Endpoint triggered by the 'Refresh' button on the UI."""
    result = await netsuite_handler.main(created_at_min=payload.created_at_min)
    return result

@app.post("/api/update-assignment")
async def update_machine_assignment(payload: AssignmentPayload):
    """Endpoint to assign a WO to a machine or toggle printing."""
    success = await db_handler.update_assignment(
        machine_id=payload.machine_id,
        work_order_id=payload.work_order_id,
        is_active=payload.is_printing_active
    )
    if success:
        return {"status": "success", "message": "Assignment updated."}
    else:
        return {"status": "error", "message": "Failed to update assignment."}

@app.get("/api/debug/print-log")
async def debug_get_print_log():
    """Debug endpoint to fetch all print log entries."""
    async with db_handler.engine.connect() as conn:
        result = await conn.execute(db_handler.text("SELECT * FROM print_log ORDER BY id DESC"))
        logs = [dict(row._mapping) for row in result.all()]
        return logs

@app.get("/api/failed-prints")
async def get_failed_prints():
    """Endpoint to fetch failed print log entries."""
    async with db_handler.engine.connect() as conn:
        # Fetch relevant columns for failed prints, including zpl_content
        stmt = db_handler.text("""
            SELECT id, serial_number, work_order_no, machine_id, print_timestamp, error_message, zpl_content
            FROM print_log
            WHERE print_status = 'FAILED'
            ORDER BY print_timestamp DESC
            LIMIT 50
        """) # Limit to last 50 failed prints for performance
        result = await conn.execute(stmt)
        failed_prints = [dict(row._mapping) for row in result.all()]
        return failed_prints