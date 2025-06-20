# mqtt_service.py
import paho.mqtt.client as mqtt_client
from paho.mqtt.enums import CallbackAPIVersion
import logging
import asyncio
import json
import time
# from collections import deque # No longer needed

import config
from db_handler import get_assignment_for_machine, log_print_event, log_raw_mqtt_message # Import new function
from label_printer import print_coil_label, generate_serial_number

# Global deque to store recent MQTT messages - REMOVED
# MQTT_LOG_MAX_LENGTH = 50
# mqtt_message_log = deque(maxlen=MQTT_LOG_MAX_LENGTH)
# mqtt_log_lock = asyncio.Lock() # To ensure thread-safe appends to the deque - REMOVED

def connect_mqtt():
    """Connects to the MQTT broker and returns the client instance."""
    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            logging.info(f"Connected to MQTT Broker. Subscribing to topics: {config.MQTT_PRINT_TOPICS}")
            for topic_filter in config.MQTT_PRINT_TOPICS:
                client.subscribe(topic_filter)
                logging.info(f"Subscribed to {topic_filter}")
        else:
            logging.error(f"Failed to connect to MQTT, return code {rc}")

    if not config.MQTT_BROKER_HOST:
        logging.error("MQTT_BROKER_HOST is not set in the configuration.")
        return None

    client = mqtt_client.Client(callback_api_version=CallbackAPIVersion.VERSION2, client_id=f"python-mqtt-listener-{int(time.time())}")
    if config.MQTT_USERNAME and config.MQTT_PASSWORD:
        client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
    
    client.on_connect = on_connect
    
    try:
        client.connect(config.MQTT_BROKER_HOST, config.MQTT_BROKER_PORT)
    except Exception as e:
        logging.error(f"Error connecting to MQTT broker: {e}")
        return None
        
    return client

async def on_message_received(topic: str, payload_str: str):
    """Callback for when a message is received from MQTT."""
    # Log to database instead of in-memory deque
    current_timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    try:
        # We call this first to ensure the raw message is logged even if subsequent processing fails
        await log_raw_mqtt_message(current_timestamp, topic, payload_str)
    except Exception as e:
        logging.error(f"Failed to log raw MQTT message to DB: {e}")
        # Decide if you want to return or continue processing if DB log fails
        # For now, we'll log the error and continue attempting to process for printing

    logging.info(f"Received from topic `{topic}`: {payload_str}") # Standard logging continues
    
    try: # This try is for the main message processing logic
        data = json.loads(payload_str).get("d", {})
        # The machine ID is the last part of the topic for Print_AutoCoiler
        # Extract machine_id from the end of the topic string (e.g., "malhotra/Print_AutoCoiler1" -> 1)
        try:
            machine_id_str = topic[-1] # Get the last character
            if not machine_id_str.isdigit(): # Basic validation if it's not a digit from the topic name
                 # Fallback or more robust parsing if needed, e.g. regex, or check against a known list of full topic names
                 # For now, we'll try to find a digit at the end of the topic string
                 import re
                 match = re.search(r'\d+$', topic)
                 if match:
                     machine_id_str = match.group(0)
                 else: # If no digit found at the end, this parsing will fail.
                      logging.error(f"Could not parse machine_id from topic: {topic}")
                      return
            machine_id = int(machine_id_str)
        except ValueError:
            logging.error(f"Could not parse machine_id from topic: {topic}. Expected a number at the end.")
            return
        except IndexError:
            logging.error(f"Topic string too short to parse machine_id: {topic}")
            return
        
        # 1. Check for Active Assignment
        assignment = await get_assignment_for_machine(machine_id)

        if not assignment or not assignment['is_printing_active']:
            logging.warning(f"No active assignment for machine {machine_id}. Ignoring print trigger.")
            return

        # 2. We have an active assignment, proceed with printing
        work_order_details = assignment['work_order_data'] # This will be the full JSON for the WO
        
        # 3. Generate Serial Number
        serial_number = await generate_serial_number(machine_id)

        # 4. Determine Defect Type
        defect_type = "None"
        if data.get('spark', [False])[0]: defect_type = "Spark"
        if data.get('diameter', [False])[0]: defect_type = "Diameter"
        # ... add more logic if needed

        # 5. Assemble Label Data
        label_data = {
            "serial_number": serial_number,
            "product_id": work_order_details.get("mcpl_part_code", "N/A"),
            "customer_product_code": work_order_details.get("customer_part_code", "N/A"),
            "customer_name": work_order_details.get("customer_name", "N/A"),
            "actual_length": data.get('pre_coil_length', [0])[0],
            "defect_type": defect_type
        }
        
        # 6. Print and Log
        # Run the synchronous print_coil_label in a thread pool executor
        loop = asyncio.get_running_loop()
        # print_coil_label now returns: (success_status, error_message, zpl_code)
        print_ok, error_msg, zpl_code = await loop.run_in_executor(None, print_coil_label, label_data)
        
        await log_print_event(
            machine_id=machine_id,
            work_order_no=work_order_details.get("work_order_no"),
            label_data=label_data,
            payload_str=payload_str,
            is_success=print_ok,
            error_message=error_msg,
            zpl_content=zpl_code # Pass the ZPL code
        )

    except Exception as e:
        logging.error(f"Error processing MQTT message on topic {topic}: {e}")
    
def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - MQTT - %(levelname)s - %(message)s')
    logging.info("Starting MQTT Listener Service...")
    client = connect_mqtt()

    if not client:
        logging.error("Could not create MQTT client. Exiting.")
        return
    
    loop = asyncio.get_event_loop()
    client.user_data_set(loop) # Make the loop accessible in callbacks via userdata

    def on_message_wrapper(client, userdata, msg):
        event_loop = userdata # Retrieve the loop passed via userdata
        asyncio.run_coroutine_threadsafe(
            on_message_received(msg.topic, msg.payload.decode()),
            event_loop
        )

    client.on_message = on_message_wrapper
    client.loop_start() # Starts a new thread for the MQTT network loop

    try:
        # Run the asyncio event loop in the main thread
        loop.run_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down MQTT service (KeyboardInterrupt)...")
    finally:
        logging.info("Stopping MQTT client loop...")
        client.loop_stop()
        logging.info("MQTT client loop stopped.")
        
        # Gracefully stop the asyncio event loop
        # Gather all remaining tasks and cancel them
        if loop.is_running():
            logging.info("Stopping asyncio event loop...")
            tasks = asyncio.all_tasks(loop=loop)
            for task in tasks:
                task.cancel()
            # Allow tasks to be cancelled
            # loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True)) # This might hang if tasks don't handle cancellation well
            # A simpler stop for this script:
            loop.call_soon_threadsafe(loop.stop)
            # loop.stop() # This should be called from within the loop or via call_soon_threadsafe
            # Wait a bit for loop to stop if call_soon_threadsafe was used
            # time.sleep(1) # Give it a moment
            if not loop.is_closed(): # Check if it's not already closed
                 # Ensure all tasks are done before closing loop, or close might raise errors
                 # For this script, a direct stop might be okay if on_message_received tasks are short-lived
                 # or handle cancellation properly.
                 pass # loop.close() # Can be problematic if tasks are still pending
            logging.info("Asyncio event loop stopped.")

if __name__ == '__main__':
    main()