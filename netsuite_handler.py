import requests
import json
import sys
import subprocess
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

# ===============================================================================
# CONFIGURATION SECTION
# ===============================================================================
# NetSuite account configuration
ACCOUNT_ID = os.getenv("ACCOUNT_ID")
if not ACCOUNT_ID:
    raise ValueError("ACCOUNT_ID not found in .env file")

# Your integration credentials (from your partner's successful example)
CONSUMER_KEY = os.getenv("CONSUMER_KEY")
if not CONSUMER_KEY:
    raise ValueError("CONSUMER_KEY not found in .env file")

# Certificate information
CERTIFICATE_ID = os.getenv("CERTIFICATE_ID")
if not CERTIFICATE_ID:
    raise ValueError("CERTIFICATE_ID not found in .env file")

# RESTlet information
script_id_str = os.getenv("SCRIPT_ID")
if not script_id_str:
    raise ValueError("SCRIPT_ID not found in .env file")
SCRIPT_ID = int(script_id_str)

deploy_id_str = os.getenv("DEPLOY_ID")
if not deploy_id_str:
    raise ValueError("DEPLOY_ID not found in .env file")
DEPLOY_ID = int(deploy_id_str)
CREATED_AT_MIN = os.getenv("CREATED_AT_MIN")
if not CREATED_AT_MIN:
    raise ValueError("CREATED_AT_MIN not found in .env file")

# NetSuite endpoints
TOKEN_URL = f"https://{ACCOUNT_ID}.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token"
RESTLET_URL = f"https://{ACCOUNT_ID}.restlets.api.netsuite.com/app/site/hosting/restlet.nl"

# Node.js script path
JWT_GENERATOR_PATH = "jwt_generator.js" # This path remains local to the Python script

# ===============================================================================
# UTILITY FUNCTIONS - Helper functions for logging and debugging
# ===============================================================================

def log_section(title):
    """Print a section header with title."""
    width = 80
    print("\n" + "=" * width)
    print(f" {title} ".center(width, "="))
    print("=" * width)

def log_step(step_num, description):
    """Print a step header."""
    print(f"\n[STEP {step_num}] {description}")
    print("-" * 80)

def log_info(message):
    """Print an info message."""
    print(f"[INFO] {message}")

def log_warning(message):
    """Print a warning message."""
    print(f"[WARNING] {message}")

def log_error(message):
    """Print an error message."""
    print(f"[ERROR] {message}")

def log_success(message):
    """Print a success message."""
    print(f"[SUCCESS] {message}")

def log_json(label, data):
    """Print JSON data with proper formatting."""
    print(f"[JSON] {label}:")
    print(json.dumps(data, indent=2))

def log_request(method, url, headers, data=None):
    """Log details of a request being made."""
    print(f"[REQUEST] {method} {url}")
    print("Request Headers:")
    for key, value in headers.items():
        print(f"  {key}: {value}")
    
    if data:
        if isinstance(data, dict):
            print("Request Data (JSON):")
            print(json.dumps(data, indent=2))
        else:
            # For form data, don't print actual JWT which could be very long
            if "client_assertion" in data:
                sanitized = data.replace(data.split("client_assertion=")[1], "[JWT_CONTENT]")
                print(f"Request Data (Form): {sanitized}")
            else:
                print(f"Request Data: {data}")

def log_response(response):
    """Log details of a response received."""
    print(f"[RESPONSE] Status Code: {response.status_code}")
    print("Response Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    
    if response.text:
        try:
            json_data = response.json()
            print("Response Body (JSON):")
            print(json.dumps(json_data, indent=2))
        except:
            print(f"Response Body: {response.text}")

# ===============================================================================
# JWT GENERATION - Generate JWT using Node.js
# ===============================================================================

def check_nodejs_installed():
    """Check if Node.js is installed."""
    try:
        result = subprocess.run(['node', '--version'], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                text=True)
        if result.returncode == 0:
            log_success(f"Node.js is installed: {result.stdout.strip()}")
            return True
        else:
            log_error("Node.js check failed")
            return False
    except FileNotFoundError:
        log_error("Node.js is not installed or not in PATH")
        return False

def generate_jwt():
    """Generate JWT using Node.js script."""
    log_step(2, "Generating JWT using Node.js")
    
    if not os.path.exists(JWT_GENERATOR_PATH):
        log_error(f"Node.js JWT generator script not found: {JWT_GENERATOR_PATH}")
        return None
    
    try:
        result = subprocess.run(['node', JWT_GENERATOR_PATH], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                text=True)
        
        if result.returncode == 0:
            jwt = result.stdout.strip()
            log_success(f"JWT generated successfully using Node.js")
            log_info(f"JWT length: {len(jwt)}")
            log_info(f"JWT:{jwt}")
            #log_info(f"JWT last 50 chars: ...{jwt[-50:]}")
            return jwt
        else:
            log_error(f"Node.js script failed with error: {result.stderr}")
            return None
    except Exception as e:
        log_error(f"Error running Node.js script: {e}")
        return None

# ===============================================================================
# OAUTH AUTHENTICATION - Get access token
# ===============================================================================

def get_access_token():
    """Get an access token using client credentials grant type with JWT assertion."""
    log_step(3, "Requesting access token with JWT")
    
    jwt = generate_jwt()
    if not jwt:
        log_error("Failed to generate JWT - cannot proceed")
        return None
    
    # Format data exactly as it appears in the Postman request
    data = f"grant_type=client_credentials&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth%3Aclient-assertion-type%3Ajwt-bearer&client_assertion={jwt}"
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    log_request("POST", TOKEN_URL, headers, data)
    
    try:
        response = requests.post(TOKEN_URL, headers=headers, data=data)
        log_response(response)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in")
            token_type = token_data.get("token_type")
            
            log_success(f"Access token obtained (expires in {expires_in} seconds)")
            log_info(f"Token type: {token_type}")
            log_info(f"Access token first 20 chars: {access_token[:20]}...")
            
            return access_token
        else:
            log_error(f"Failed to get access token. Status code: {response.status_code}")
            return None
    except Exception as e:
        log_error(f"Exception getting access token: {e}")
        return None

# ===============================================================================
# RESTLET CONNECTION - Test connection to RESTlet
# ===============================================================================

def test_connection(access_token):
    """Test connection to NetSuite RESTlet using the access token."""
    log_step(4, "Testing connection to RESTlet")
    
    if not access_token:
        log_error("No access token available - cannot connect to RESTlet")
        return False
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "script": SCRIPT_ID,
        "deploy": DEPLOY_ID,
        "created_at_min": CREATED_AT_MIN
    }
    
    payload = {
        "Status": "Connection"
    }
    
    # Build the full URL with parameters
    url = f"{RESTLET_URL}?script={SCRIPT_ID}&deploy={DEPLOY_ID}&created_at_min={CREATED_AT_MIN}"
    log_info(f"DEBUG: RESTLET_URL (POST): {RESTLET_URL}")
    log_info(f"DEBUG: Constructed URL (POST): {url}")
    log_request("POST", url, headers, payload)
    
    try:
        response = requests.post(
            RESTLET_URL, 
            headers=headers, 
            params=params, 
            data=json.dumps(payload)
        )
        
        log_response(response)
        
        if response.status_code == 200:
            log_success("Connection to RESTlet successful!")
            return True
        else:
            log_error(f"Connection to RESTlet failed with status code: {response.status_code}")
            return False
    except Exception as e:
        log_error(f"Exception testing connection: {e}")
        return False

async def get_restlet_data(access_token, created_at_min_date):
    """Send a GET request to NetSuite RESTlet and display the response."""
    log_step(5, f"Sending GET request to RESTlet for created_at_min={created_at_min_date}")

    if not access_token:
        log_error("No access token available - cannot send GET request to RESTlet")
        return False

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Build the full URL with parameters for GET request
    url = f"{RESTLET_URL}?script={SCRIPT_ID}&deploy={DEPLOY_ID}&created_at_min={created_at_min_date}"
    log_info(f"DEBUG: RESTLET_URL (GET): {RESTLET_URL}")
    log_info(f"DEBUG: Constructed URL (GET): {url}")
    log_request("GET", url, headers) # No payload for GET request

    try:
        response = requests.get(
            url,
            headers=headers
        )

        log_response(response)

        if response.status_code == 200:
            log_success(f"GET request to RESTlet successful for created_at_min={created_at_min_date}!")
            
            # Save the work orders to the database
            from db_handler import save_work_orders
            import asyncio
            
            work_order_data = response.json()
            all_work_orders = work_order_data.get("Work_order_list", [])
            
            await save_work_orders(all_work_orders)
            
            return True
        else:
            log_error(f"GET request to RESTlet failed with status code: {response.status_code}")
            return False
    except Exception as e:
        log_error(f"Exception sending GET request: {e}")
        return False

# ===============================================================================
# MAIN EXECUTION
# ===============================================================================

async def main(created_at_min=None):
    """Main execution function."""
    log_section("NETSUITE API CONNECTION TEST (NODE.JS JWT APPROACH)")
    log_info(f"Account ID: {ACCOUNT_ID}")
    log_info(f"Certificate ID: {CERTIFICATE_ID}")
    log_info(f"RESTlet: script={SCRIPT_ID}, deploy={DEPLOY_ID}")
    
    # Step 1: Check if Node.js is installed
    log_step(1, "Checking Node.js installation")
    if not check_nodejs_installed():
        log_error("Node.js is required to run this script")
        log_info("Please install Node.js from https://nodejs.org/")
        return False
    
    # Step 2 & 3: Generate JWT and get access token
    access_token = get_access_token()
    
    if not access_token:
        log_error("Failed to get access token - cannot proceed")
        return False
    
    # Step 4: Test POST connection to RESTlet
    post_success = test_connection(access_token)
    
    # Step 5: Get user input for created_at_min and send GET request to RESTlet
    get_success = False
    if post_success: # Only proceed with GET if POST was successful
        if not created_at_min:
            log_warning("No date entered for GET request. Skipping GET request.")
        else:
            get_success = await get_restlet_data(access_token, created_at_min)
    
    if post_success and get_success:
        log_section("CONNECTION TEST SUMMARY")
        log_success("All steps completed successfully (POST and GET)!")
        log_info("Your connection to NetSuite RESTlet is working properly")
        return True
    else:
        log_section("CONNECTION TEST SUMMARY")
        log_error("Connection test failed (POST or GET)")
        log_info("Check the error messages above for troubleshooting")
        return False
 
if __name__ == "__main__":
    try:
        # When running as a script, we need to run the async main function
        import asyncio
        success = asyncio.run(main())
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        log_warning("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        sys.exit(1)