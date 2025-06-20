import sqlite3
import socket
import logging

# --- CONFIG ---
DB_NAME = "labelprinting.db"
PRINTER_IP = "192.168.1.100"  # Replace with your Zebra printer IP
PRINTER_PORT = 9100           # Default ZPL port

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def list_machines(cursor):
    cursor.execute("SELECT machine_id, equipment_name FROM machine_assignments")
    machines = cursor.fetchall()
    print("\nAvailable Machines:")
    for m in machines:
        print(f"{m[0]}: {m[1]}")

def choose_print_mode():
    print("\nHow would you like to print?")
    print("1. Print latest label from a specific machine")
    print("2. Print by serial number")
    return input("Enter choice (1 or 2): ")

def get_latest_label_for_machine(cursor, machine_id):
    cursor.execute("""
        SELECT serial_number, zpl_content
        FROM print_log
        WHERE machine_id = ?
        ORDER BY print_timestamp DESC
        LIMIT 1
    """, (machine_id,))
    return cursor.fetchone()

def get_label_by_serial(cursor, serial):
    cursor.execute("""
        SELECT serial_number, zpl_content
        FROM print_log
        WHERE serial_number = ?
    """, (serial,))
    return cursor.fetchone()

def send_zpl_to_printer(zpl: str) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((PRINTER_IP, PRINTER_PORT))
            s.sendall(zpl.encode("utf-8"))
        logging.info("✅ ZPL sent to printer.")
        return True
    except Exception as e:
        logging.error(f"❌ Failed to send ZPL: {e}")
        return False

def main():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        choice = choose_print_mode()

        if choice == "1":
            list_machines(cursor)
            machine_id = int(input("Enter machine ID: "))
            result = get_latest_label_for_machine(cursor, machine_id)
            if result:
                serial_number, zpl = result
            else:
                print("⚠️ No label found for that machine.")
                return

        elif choice == "2":
            serial_number = input("Enter serial number: ").strip()
            result = get_label_by_serial(cursor, serial_number)
            if result:
                serial_number, zpl = result
            else:
                print("⚠️ Serial number not found.")
                return
        else:
            print("Invalid choice.")
            return

        confirm = input(f"\nSend label for S/N {serial_number} to printer? (y/n): ").lower()
        if confirm == 'y':
            send_zpl_to_printer(zpl)
        else:
            print("🛑 Print cancelled.")

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
