import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_NAME = "labelprinting.db"

# --- SQLite-compatible Schema ---
# Note: MySQL-specific features have been adapted for SQLite.
SQL_SCHEMA = """
-- Table to store a local, de-duplicated cache of NetSuite work orders
CREATE TABLE IF NOT EXISTS `work_orders` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `work_order_no` TEXT NOT NULL UNIQUE,
  `mcpl_part_code` TEXT,
  `customer_part_code` TEXT,
  `customer_name` TEXT,
  `total_quantity` TEXT,
  `mfg_process_name` TEXT,
  `raw_json_data` TEXT NOT NULL,
  `location` TEXT,
  `wire_type` TEXT,
  `guage` TEXT,
  `main_color` TEXT,
  `bi_color` TEXT,
  `work_order_date` TEXT,
  `last_fetched_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table to manage the CURRENT state of machine assignments
CREATE TABLE IF NOT EXISTS `machine_assignments` (
  `machine_id` INTEGER PRIMARY KEY,
  `equipment_name` TEXT NOT NULL,
  `assigned_work_order_id` INTEGER,
  `is_printing_active` INTEGER NOT NULL DEFAULT 0, -- Using INTEGER for BOOLEAN
  `last_updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`assigned_work_order_id`) REFERENCES `work_orders`(`id`)
);

-- Table to log every printed label for auditing
CREATE TABLE IF NOT EXISTS `print_log` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `serial_number` TEXT NOT NULL UNIQUE,
  `machine_id` INTEGER NOT NULL,
  `work_order_no` TEXT NOT NULL,
  `product_id` TEXT NOT NULL,
  `actual_length` INTEGER,
  `defect_type` TEXT,
  `mqtt_payload` TEXT,
  `print_timestamp` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `print_status` TEXT NOT NULL CHECK(print_status IN ('SUCCESS', 'FAILED')),
  `error_message` TEXT,
  `zpl_content` TEXT NULL
);

-- Table for serial number generation
CREATE TABLE IF NOT EXISTS `serial_number_counter` (
    `counter_date` DATE PRIMARY KEY,
    `last_sequence` INT NOT NULL
);

-- Table for raw MQTT message logging
CREATE TABLE IF NOT EXISTS `mqtt_raw_log` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `timestamp` TEXT NOT NULL,
  `topic` TEXT NOT NULL,
  `payload` TEXT NOT NULL
);
"""

# --- Initial Data ---
SQL_INITIAL_DATA = """
-- Pre-populate the assignment table with your 5 machines
INSERT OR IGNORE INTO `machine_assignments` (machine_id, equipment_name) VALUES
(1, 'Autocoiler-1'),
(2, 'Autocoiler-2'),
(3, 'Autocoiler-3'),
(4, 'Autocoiler-4'),
(5, 'Autocoiler-5');
"""

def create_database():
    """Creates the SQLite database and tables."""
    try:
        logging.info(f"Creating database '{DB_NAME}'...")
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Enable foreign key support
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Execute the schema creation script
        logging.info("Executing schema...")
        cursor.executescript(SQL_SCHEMA)

        # Insert initial data
        logging.info("Inserting initial data...")
        cursor.executescript(SQL_INITIAL_DATA)

        conn.commit()
        logging.info("Database and tables created successfully.")

    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    create_database()