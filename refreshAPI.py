# from flask import Flask, jsonify
import schedule
import subprocess
import time
import gc
import logging
from datetime import datetime, timedelta
import shelve
import atexit
import os
import sys

# app = Flask(__name__)

# Set up logging
LOG_FILE = "refresh_server.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Function to run the data refresh script
def run_data_refresh():
    """Calls the dataRefresh2.py script as a separate process."""
    try:
        logging.info("Starting data refresh...")
        subprocess.run(["python", "dataRefresh2.py"], check=True)
        gc.collect()
    except subprocess.CalledProcessError as e:
        logging.error(f"Data refresh failed: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during data refresh: {e}")

# Function to schedule the data refresh task
def schedule_data_refresh():
    """Schedules the data refresh task to run every 2 minutes."""
    schedule.every(1).minutes.do(run_data_refresh)
    while True:
        try:
            schedule.run_pending()
            time.sleep(3)  # Sleep for 1 second to avoid high CPU usage
        except Exception as e:
            logging.error(f"Error in scheduling loop: {e}")

# Flask route to check the status of the server
# @app.route('/status', methods=['GET'])
# def status():
#     """Returns the status of the server and logs."""
#     try:
#         # Read the last 2 days of logs
#         with open(LOG_FILE, "r") as log_file:
#             logs = log_file.readlines()

#         # Filter logs from the last 2 days
#         two_days_ago = datetime.now() - timedelta(days=2)
#         recent_logs = [
#             log for log in logs if datetime.strptime(log.split(" - ")[0], "%Y-%m-%d %H:%M:%S") >= two_days_ago
#         ]

#         return jsonify({"status": "Data refresh server is running.", "logs": recent_logs})
#     except FileNotFoundError:
#         return jsonify({"status": "Data refresh server is running.", "logs": "No logs available."})
#     except Exception as e:
#         logging.error(f"Error reading logs: {e}")
#         return jsonify({"status": "Error retrieving logs.", "error": str(e)})

def deleteRefresherDB():
    """Deletes the 'refreshCheckDB.db' file or directory on program exit."""
    try:
        if os.path.exists('refreshCheckDB.db'):
            if os.path.isfile('refreshCheckDB.db'):
                os.remove('refreshCheckDB.db')
                print("File 'refreshCheckDB.db' deleted.")
            elif os.path.isdir('refreshCheckDB.db'):
                os.rmdir('refreshCheckDB.db')
                print("Directory 'refreshCheckDB.db' deleted.")
    except Exception as e:
        print(f"Error during cleanup: {e}")

# Register the cleanup function to run on program exit
atexit.register(deleteRefresherDB)

# Start the scheduler when the Flask app starts
if __name__ == "__main__":
    try:
        # Start the scheduler directly in the main thread
        print("Starting data refresh scheduled on 1 minute intervals...")
        schedule_data_refresh()

        # Note: The Flask app.run() won't be reached because schedule_data_refresh() runs indefinitely
        # This is intentional as we want the scheduling to be the main process
        
    except KeyboardInterrupt:
        print("\nProcess interrupted. Cleaning up...")
    finally:
        deleteRefresherDB()