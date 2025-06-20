# import asyncio # No longer needed for win32print
import win32print
import logging
from datetime import datetime
import config
from db_handler import get_next_serial_sequence

def _get_qa_status_text(defect_type: str) -> str:
    """Translates defect type into a QA status string for the label."""
    # In your Java code, it seems qaStatus=1 means no text.
    # We'll assume any defect means it's not status 1.
    if defect_type == "None":
        return ""
    # Return a concise code for the label if there's a defect
    return " (QA HOLD)"
    
async def generate_serial_number(machine_id: int) -> str:
    """
    Generates a unique serial number in the format YYMMDD-MACHINE_ID-XXXX.
    """
    today_str = datetime.now().strftime("%y%m%d")
    sequence = await get_next_serial_sequence() # This function will handle the DB transaction
    
    # Format the sequence with leading zeros, e.g., 1 -> "0001"
    sequence_str = f"{sequence:04d}" 
    
    # Example: 250614-1-0001
    serial_number = f"{today_str}-{machine_id}-{sequence_str}"
    return serial_number

def print_coil_label(label_data: dict): # Changed to synchronous
    """
    Formats the final label data into ZPL and sends it to the printer.
    This ZPL template is a direct Python translation of your Java example.
    """
    
    # 1. Unpack all data points from the dictionary for clarity
    plant_code = label_data.get("plant_code", "N/A")
    wire_type = label_data.get("wire_type", "N/A")
    fg_part_no = label_data.get("product_id", "N/A")
    description = label_data.get("description", "N/A")
    size_str = str(label_data.get("size", "0"))
    size_uom = label_data.get("size_uom", "mm")
    color = label_data.get("color", "N/A")
    lot_no = label_data.get("lot_no", "N/A")
    length = label_data.get("actual_length", 0)
    length_uom = label_data.get("length_uom", "mtr")
    po_no = label_data.get("po_no", "N/A")
    operator_name = label_data.get("operator_name", "System")
    print_date = datetime.now().strftime("%d-%m-%Y")
    serial_no = label_data.get("serial_number", "ERROR_SN")
    client_name = label_data.get("customer_name", "N/A")
    defect_type = label_data.get("defect_type", "None")
    
    # Handle derived fields
    qa_text = _get_qa_status_text(defect_type)
    
    # Example parsing for 'strands' and 'diameter' from wire_type 'FLRY-A T2 (7/0.21)'
    # This logic needs to be robust based on your actual data formats.
    try:
        parts = wire_type.split('/')
        strands = parts[0][-1] # Get the last character of the first part
        diameter = parts[1].split(')')[0]
        type_str = f"{wire_type} ({strands}/{diameter})"
    except:
        strands, diameter, type_str = '?', '?', wire_type
        
    # 2. Construct the ZPL string using an f-string
    # This is a direct translation of the ZPL from your Java code.
    # We use triple quotes for a multi-line string.
    zpl_string = f"""
    ^XA~TA000~JSN^LT0^MNW^MTT^PON^PMN^LH0,0^JMA^PRA,8~SD15^JUS^LRN^CI27^PA0,1,1,0^XZ
    ^XA
    ^MMT
    ^PW799
    ^LL400
    ^LS0
    ^FO17,43^GB690,351,2^FS
    ^FT31,73^A0N,23,23^FH^CI28^FD{description}^FS^CI27
    ^FT257,73^A0N,23,25^FH^CI28^FD{type_str}^FS^CI27
    ^FT31,132^A0N,23,23^FH^CI28^FDSIZE^FS^CI27
    ^FT257,130^A0N,23,23^FH^CI28^FD{size_str} {size_uom}^FS^CI27
    ^FT31,161^A0N,23,23^FH^CI28^FDCOLOUR^FS^CI27
    ^FT257,161^A0N,23,23^FH^CI28^FD{color}^FS^CI27
    ^FT31,217^A0N,23,23^FH^CI28^FDCUSTOMER^FS^CI27
    ^FT255,217^A0N,23,23^FH^CI28^FD{client_name}^FS^CI27
    ^FT31,187^A0N,23,23^FH^CI28^FDLOT NO^FS^CI27
    ^FT257,187^A0N,23,23^FH^CI28^FD{lot_no}^FS^CI27
    ^FT31,246^A0N,23,23^FH^CI28^FDCOIL LENGTH^FS^CI27
    ^FT257,246^A0N,23,19^FH^CI28^FD{length} {length_uom}{qa_text}^FS^CI27
    ^FT31,306^A0N,23,23^FH^CI28^FDP.O No^FS^CI27
    ^FT255,306^A0N,23,23^FH^CI28^FD{po_no}^FS^CI27
    ^FT31,277^A0N,23,23^FH^CI28^FDOPERATOR^FS^CI27
    ^FT257,275^A0N,23,23^FH^CI28^FD{operator_name}^FS^CI27
    ^FT32,367^A0N,20,13^FH^CI28^FDMfg By^FS^CI27
    ^BY1,3,50^FT477,105^BCN,,N,N^FH^FD{fg_part_no}^FS
    ^FT257,96^A0N,23,20^FH^CI28^FD{fg_part_no}^FS^CI27
    ^FT31,337^A0N,23,23^FH^CI28^FDDATE^FS^CI27
    ^FT257,337^A0N,23,23^FH^CI28^FD{print_date}^FS^CI27
    ^FT257,370^A0N,23,23^FH^CI28^FD{serial_no}^FS^CI27
    ^FT31,103^A0N,23,23^FH^CI28^FDFG PART NO^FS^CI27
    ^FT480,390^BQN,2,4^FH^FDPLAP{fg_part_no}|Q{length}|S{serial_no}|D{print_date}|L{lot_no}^FS
    ^BY1,3,41^FT480,180^BCN,,N,N^FH^FD{length} {length_uom}^FS
    ^FO248,54^GB0,335,3^FS
    ^FO708,84^GFA,257,3540,12,:Z64:eJztlzEOwjAMRV2CVIklNyA7l8jR2qNk7iXIcTpmRCgCYsexu7AxMDhLn37V99qxAJetnRXohHc7HcE3fMGPdvOb3/zmN7/5zW9+85vf/H/sv213ZPozoJXveEZ8YmaubXfMj8YTc0ER8468dM7IsXOSLIe96Eeg0u5EPwKlv7PqOZA7R9F//95Z9D3wZJ5UT4F98CJ6CqTBQfQYGHoMVNmd6DFQDiz6FsjKMSkHRbiuyufDfuLrBxF0zD0=:0104^FS
    ^FT712,28^A0N,20,20^FH^CI28^FDINSERT^FS^CI27
    ^FT723,49^A0N,20,20^FH^CI28^FDTHIS^FS^CI27
    ^FT723,70^A0N,20,20^FH^CI28^FDWAY^FS^CI27
    ^FT78,370^A0N,27,20^FH^CI28^FDMCPL - {plant_code}^FS^CI27
    ^FT408,33^A0N,25,25^FH^CI28^FDFINISH GOODS BARCODE^FS^CI27
    ^FT62,33^A0N,25,25^FH^CI28^FDMALHOTRA CABLES^FS^CI27
    ^PQ1,0,1,Y
    ^XZ
    """
    
    # 3. Send to printer
    printer_name = config.PRINTER_IP # PRINTER_IP from .env should be the UNC path like \\server\printer
    
    if not printer_name:
        error_msg = "PRINTER_IP is not set in the environment or .env file. Cannot print."
        logging.error(error_msg)
        # Ensure zpl_string is defined even if we return early.
        # It might not be if generate_serial_number or other parts failed before this.
        # For safety, let's assume label_data and serial_no are available to construct a placeholder.
        # However, the current structure defines zpl_string before this block.
        # If zpl_string might not be defined, we'd need to handle that.
        # For now, assuming zpl_string is defined from earlier in the function.
        # serial_no = label_data.get("serial_number", "UNKNOWN_SN_FOR_ERROR") # Get serial_no if not already available
        # zpl_string_placeholder = f"^XA^FO50,50^ADN,36,20^FDPRINTER_IP NOT SET: {serial_no}^FS^XZ"
        return False, error_msg, "ZPL_NOT_GENERATED_PRINTER_IP_MISSING" # Return a placeholder ZPL or handle as needed

    logging.info(f"Attempting to print to Windows shared printer: {printer_name} for S/N: {serial_no}")

    try:
        # printer_name is now checked and should be a string if we reach here.
        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            # Job name can be anything descriptive, using serial number here
            job_info = (f"ZPL_Coil_{serial_no}", None, "RAW") # pDocName is the first element for StartDocPrinter level 1
            # The StartDocPrinter pDocInfo level 1 expects a tuple: (pDocName, pOutputFile, pDatatype)
            # pOutputFile can be an empty string to print to the device. pDatatype "RAW" for ZPL.
            doc_info_level_1 = (f"ZPL_Coil_{serial_no}", "", "RAW")

            hJob = win32print.StartDocPrinter(hPrinter, 1, doc_info_level_1)
            try:
                win32print.StartPagePrinter(hPrinter)
                # ZPL data needs to be bytes
                bytes_to_send = zpl_string.encode('utf-8')
                bytes_written = win32print.WritePrinter(hPrinter, bytes_to_send)
                logging.info(f"Sent {bytes_written} bytes of ZPL for S/N: {serial_no}")
                win32print.EndPagePrinter(hPrinter)
            finally:
                win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
        
        logging.info(f"Successfully sent ZPL to printer {printer_name} for S/N: {serial_no}")
        return True, None, zpl_string
    except Exception as e:
        # Catch specific win32print errors if needed, or general Exception
        error_msg = f"Failed to send ZPL to Windows shared printer {printer_name}. Error: {e}"
        logging.error(error_msg)
        # Log the ZPL string if printing fails for debugging
        logging.debug(f"Failed ZPL for S/N {serial_no}:\n{zpl_string}")
        return False, error_msg, zpl_string