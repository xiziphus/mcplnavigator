# db_handler.py
import aiomysql
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import json
import logging
from datetime import date
from typing import Optional
import config

engine = create_async_engine(config.DATABASE_URL)

async def get_next_serial_sequence() -> int:
    """Atomically gets and increments the serial number for the current day."""
    today = date.today()
    async with engine.begin() as conn: # begin() starts a transaction
        # Insert or update the counter for today
        stmt_upsert = text("""
            INSERT INTO serial_number_counter (counter_date, last_sequence)
            VALUES (:today, 1)
            ON CONFLICT(counter_date) DO UPDATE SET last_sequence = last_sequence + 1;
        """)
        await conn.execute(stmt_upsert, {"today": today})
        
        # Select the newly updated value
        stmt_select = text("SELECT last_sequence FROM serial_number_counter WHERE counter_date = :today;")
        result = await conn.execute(stmt_select, {"today": today})
        sequence = result.scalar_one()
        return sequence


async def save_work_orders(work_orders: list) -> int:
    """Saves a list of work orders from NetSuite into the local cache."""
    if not work_orders:
        return 0
    
    async with engine.begin() as conn:
        saved_count = 0
        for wo in work_orders:
            stmt = text("""
                INSERT INTO work_orders (
                    work_order_no, mcpl_part_code, customer_part_code, customer_name,
                    total_quantity, mfg_process_name, raw_json_data, location,
                    wire_type, guage, main_color, bi_color, work_order_date
                )
                VALUES (:wo_no, :mcpl, :cust_part, :cust_name, :qty, :process, :raw_json, :location, :wire_type, :guage, :main_color, :bi_color, :work_order_date)
                ON CONFLICT(work_order_no) DO UPDATE SET
                    mcpl_part_code = excluded.mcpl_part_code,
                    customer_part_code = excluded.customer_part_code,
                    customer_name = excluded.customer_name,
                    total_quantity = excluded.total_quantity,
                    mfg_process_name = excluded.mfg_process_name,
                    raw_json_data = excluded.raw_json_data,
                    location = excluded.location,
                    wire_type = excluded.wire_type,
                    guage = excluded.guage,
                    main_color = excluded.main_color,
                    bi_color = excluded.bi_color,
                    work_order_date = excluded.work_order_date,
                    last_fetched_at = CURRENT_TIMESTAMP;
            """)
            # Extract additional fields from the raw work order data (wo)
            # These might be nested, adjust .get() accordingly if needed
            await conn.execute(stmt, {
                "wo_no": wo.get("work_order_no"),
                "mcpl": wo.get("mcpl_part_code"),
                "cust_part": wo.get("customer_part_code"),
                "cust_name": wo.get("customer_name"),
                "qty": wo.get("total_quantity"),
                "process": wo.get("mfg_process_name"),
                "raw_json": json.dumps(wo), # Store the full original JSON
                "location": wo.get("location"),
                "wire_type": wo.get("wire_type"),
                "guage": wo.get("guage"),
                "main_color": wo.get("main_color"),
                "bi_color": wo.get("bi_color"),
                "work_order_date": wo.get("date") # Assuming 'date' from NetSuite is the work order date
            })
            saved_count += 1
    logging.info(f"Upserted {saved_count} work orders into local cache.")
    return saved_count

async def get_assignment_for_machine(machine_id: int) -> Optional[dict]:
    """Gets the currently assigned work order for a specific machine."""
    async with engine.connect() as conn:
        stmt = text("""
            SELECT
                ma.is_printing_active,
                wo.raw_json_data
            FROM machine_assignments ma
            JOIN work_orders wo ON ma.assigned_work_order_id = wo.id
            WHERE ma.machine_id = :machine_id;
        """)
        result = await conn.execute(stmt, {"machine_id": machine_id})
        row = result.first()
        if row:
            return {
                "is_printing_active": row.is_printing_active,
                "work_order_data": json.loads(row.raw_json_data)
            }

async def get_all_assignments():
    """Gets the current assignment status for all machines."""
    async with engine.connect() as conn:
        stmt = text("""
            SELECT
                ma.machine_id,
                ma.equipment_name,
                ma.is_printing_active,
                wo.id as work_order_id,
                wo.work_order_no,
                wo.mcpl_part_code,
                wo.total_quantity
            FROM machine_assignments ma
            LEFT JOIN work_orders wo ON ma.assigned_work_order_id = wo.id
            ORDER BY ma.machine_id;
        """)
        result = await conn.execute(stmt)
        return [row._asdict() for row in result.all()]

async def get_available_work_orders():
    """Gets all cached work orders."""
    async with engine.connect() as conn:
        stmt = text("""
            SELECT *
            FROM work_orders
            ORDER BY work_order_no;
        """)
        result = await conn.execute(stmt)
        return [row._asdict() for row in result.all()]

async def update_assignment(machine_id: int, work_order_id: int, is_active: bool):
    """Assigns a work order to a machine and sets its printing status."""
    async with engine.begin() as conn:
        stmt = text("""
            UPDATE machine_assignments
            SET assigned_work_order_id = :wo_id, is_printing_active = :is_active
            WHERE machine_id = :machine_id;
        """)
        await conn.execute(stmt, {
            "wo_id": work_order_id,
            "is_active": is_active,
            "machine_id": machine_id
        })
    logging.info(f"Updated assignment for machine {machine_id} to WO_ID {work_order_id}, printing: {is_active}")
    return True

async def log_print_event(machine_id: int, work_order_no: str, label_data: dict, payload_str: str, is_success: bool, error_message: Optional[str], zpl_content: Optional[str] = None):
    """Logs the print event to the print_log table."""
    async with engine.begin() as conn:
        stmt = text("""
            INSERT INTO print_log (
                serial_number, machine_id, work_order_no, product_id,
                actual_length, defect_type, mqtt_payload,
                print_status, error_message, zpl_content
            )
            VALUES (:sn, :mid, :wo, :pid, :len, :defect, :payload, :status, :err, :zpl)
        """)
        await conn.execute(stmt, {
            "sn": label_data["serial_number"],
            "mid": machine_id,
            "wo": work_order_no,
            "pid": label_data["product_id"],
            "len": label_data["actual_length"],
            "defect": label_data["defect_type"],
            "payload": payload_str,
            "status": "SUCCESS" if is_success else "FAILED",
            "err": error_message,
            "zpl": zpl_content
        })
    logging.info(f"Logged print event for S/N: {label_data['serial_number']}")
async def get_production_summary_for_assignment(work_order_no: str, machine_id: int) -> dict:
    """
    Calculates production summary for a given work order and machine
    from the print_log table.
    """
    summary = {
        "total_coils_produced": 0,
        "recent_coil_serial_number": None,
        "recent_coil_quantity": None,
        "total_quantity_made": 0,
        "recent_print_status": None,
        "recent_error_message": None
    }
    if not work_order_no: # Cannot get summary if no WO is assigned
        logging.debug(f"DEBUG_SUMMARY: No work_order_no provided, returning default summary.")
        return summary
    
    logging.debug(f"DEBUG_SUMMARY: Getting summary for WO: {work_order_no}, Machine: {machine_id}")

    async with engine.connect() as conn:
        # Get total coils and total quantity
        stmt_totals = text("""
            SELECT
                COUNT(*) as total_coils,
                SUM(actual_length) as total_qty
            FROM print_log
            WHERE work_order_no = :wo_no AND machine_id = :m_id;
        """)
        totals_result = await conn.execute(stmt_totals, {"wo_no": work_order_no, "m_id": machine_id})
        totals_row = totals_result.first()
        logging.debug(f"DEBUG_SUMMARY: Totals query row: {totals_row}")
        
        if totals_row:
            summary["total_coils_produced"] = totals_row.total_coils if totals_row.total_coils is not None else 0
            summary["total_quantity_made"] = totals_row.total_qty if totals_row.total_qty is not None else 0

        # Get recent coil details
        stmt_recent = text("""
            SELECT serial_number, actual_length, print_status, error_message
            FROM print_log
            WHERE work_order_no = :wo_no AND machine_id = :m_id
            ORDER BY print_timestamp DESC
            LIMIT 1;
        """)
        recent_result = await conn.execute(stmt_recent, {"wo_no": work_order_no, "m_id": machine_id})
        recent_row = recent_result.first()
        logging.debug(f"DEBUG_SUMMARY: Recent coil query row: {recent_row}")

        if recent_row:
            summary["recent_coil_serial_number"] = recent_row.serial_number
            summary["recent_coil_quantity"] = recent_row.actual_length
            summary["recent_print_status"] = recent_row.print_status
            summary["recent_error_message"] = recent_row.error_message
            
    logging.debug(f"DEBUG_SUMMARY: Final summary for WO {work_order_no}, Machine {machine_id}: {summary}")
    return summary
async def log_raw_mqtt_message(timestamp: str, topic: str, payload: str):
    """Logs a raw MQTT message to the mqtt_raw_log table."""
    async with engine.begin() as conn:
        stmt = text("""
            INSERT INTO mqtt_raw_log (timestamp, topic, payload)
            VALUES (:ts, :topic, :payload)
        """)
        await conn.execute(stmt, {"ts": timestamp, "topic": topic, "payload": payload})

async def get_recent_raw_mqtt_messages(limit: int = 50) -> list:
    """Gets the most recent raw MQTT messages from the log."""
    async with engine.connect() as conn:
        stmt = text("""
            SELECT timestamp, topic, payload
            FROM mqtt_raw_log
            ORDER BY id DESC
            LIMIT :limit
        """)
        result = await conn.execute(stmt, {"limit": limit})
        # Return as a list of dicts, but convert RowProxy to dict first
        return [dict(row._mapping) for row in result.all()]