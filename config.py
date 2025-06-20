# config.py

import os
from dotenv import load_dotenv

load_dotenv(verbose=True, override=True) # Added verbose and override for debugging

# Application Settings
APP_DEBUG = os.getenv("APP_DEBUG", "False").lower() == "true"

# MQTT Settings
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_BROKER_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_BROKER_PASSWORD")
MQTT_PRINT_TOPICS = [
    "malhotra/Print_AutoCoiler1",
    "malhotra/Print_AutoCoiler2",
    "malhotra/Print_AutoCoiler3",
    "malhotra/Print_AutoCoiler4",
    "malhotra/Print_AutoCoiler5"
]

# --- Database Settings ---
# Load individual components from .env
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))

# Construct the DATABASE_URL dynamically for SQLAlchemy
if not DB_NAME:
    raise ValueError("DB_NAME not found in .env file. Please set it.")
    
DATABASE_URL = f"sqlite+aiosqlite:///labelprinting.db"


# NetSuite API Settings
NS_ACCOUNT_ID = os.getenv("ACCOUNT_ID")
NS_CONSUMER_KEY = os.getenv("CONSUMER_KEY")
NS_CERTIFICATE_ID = os.getenv("CERTIFICATE_ID")
NS_SCRIPT_ID = os.getenv("SCRIPT_ID")
NS_DEPLOY_ID = os.getenv("DEPLOY_ID")
NS_CREATED_AT_MIN = os.getenv("CREATED_AT_MIN")
NS_PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")
NS_JWT_GENERATOR_PATH = os.getenv("JWT_GENERATOR_PATH", "jwt_generator.js")

# Printer Settings
PRINTER_IP = os.getenv("PRINTER_IP")
PRINTER_PORT = int(os.getenv("PRINTER_PORT", 9100))

# Graylog Logger Settings (Optional)
GRAYLOG_HOST = os.getenv("GRAYLOG_HOST", "localhost")
GRAYLOG_PORT = int(os.getenv("GRAYLOG_PORT", 12201))