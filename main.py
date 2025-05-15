import subprocess
import os
import shelve
import time


def start_infra_dash():
    """Starts the infraDash.py script and refreshAPI.py server."""
    print("Starting Infrastructure Monitoring Visuals ...")
    try:
        # Start the Streamlit dashboard
        dashboard_process = subprocess.Popen(
            ["streamlit", "run", "infraDash.py", "--server.address", "0.0.0.0", "--server.port", "8502"],

            stdout=None, #subprocess.PIPE,
            stderr=None, #subprocess.PIPE,
        )
        print(f"\t\tMonitoring dashboard started on port 8501.")

        # Start the Flask server for refreshAPI
        dataUpdate_process = subprocess.Popen(
            ["python", "refreshAPI.py"],
            stdout=None, #subprocess.PIPE,
            stderr=None #subprocess.PIPE,
        )
        print(f"\t\tData refresh sequence started.")


        alertNotification_process = subprocess.Popen(
            ["python", "alertApp.py"],
            stdout=None, #subprocess.PIPE,
            stderr=None #subprocess.PIPE,
        )
        print(f"\t\tNotification system started.")

            
        aiChat_process = subprocess.Popen(
                    ["python", "edgeAI_routing.py"],
                    stdout=None, #subprocess.PIPE,
                    stderr=None #subprocess.PIPE,
                )
        print(f"\t\tEdge Expert Intelligence Analysis system started.")

        dashboard_process.wait()
        dataUpdate_process.wait()
        alertNotification_process.wait()
        aiChat_process.wait()
        

    except subprocess.CalledProcessError as e:
        print(f"Error starting Dashboard Server or DataRefresh Server: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    print("Starting the application startup sequence...")
    time.sleep(2)  # Optional: Wait for 5 seconds before starting

    # Run run_at_start.py in a separate process
    try:
        subprocess.run(["python", "run_at_start.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running run_at_start.py: {e}")
        exit(1)  # Exit if run_at_start.py fails

    # Check the startNow flag in startVisuals.db
    with shelve.open('startVisuals.db') as start:
        if start.get('startNow', False):
            print("Prerequisites satisfied. Dashboard is permitted to run...")
            start_infra_dash()
        else:
            print("startNow is False. dashboard will not be started.")


# def start_infra_dash():
#     """Starts the infraDash.py script."""
#     print("Starting Infrastructure Monitoring Visuals ...")
#     try:
#         # subprocess.run(["streamlit", "run", "infraDash.py", "--server.address", "0.0.0.0", "--server.port", "50000"], check=True)
#         subprocess.run(["streamlit", "run", "infraDash.py", "--server.address", "localhost", "--server.port", "50000"], check=True)
#         subprocess.run(["python" "refreshAPI.py"], check=True)
#     except subprocess.CalledProcessError as e:
#         print(f"Error starting infraDash.py: {e}")

# # ["streamlit", "run", "infraDash.py"]

# if __name__ == "__main__":
#     print("Starting the application startup sequence...")

#     # Run run_at_start.py in a separate process
#     try:
#         subprocess.run(["python", "run_at_start.py"], check=True)
#     except subprocess.CalledProcessError as e:
#         print(f"Error running run_at_start.py: {e}")
#         exit(1)  # Exit if run_at_start.py fails

#     # Check the startNow flag in startVisuals.db
#     with shelve.open('startVisuals.db') as start:
#         if start['startNow']:
#             print("Prerequisites satisfied. Dashboard is permitted to run...")
#             start_infra_dash()
#         else:
#             print("startNow is False. infraDash.py will not be started.")

"""
1. A initial_data_load script is created to run the dataRefresh script, thus creating the EdgeDB.db and workingData.parquet files.
2. The run_at_start script is created to run the initial_data_load script only once when the app is deployed or started for the first time.
3. The main creates an order of execution for the scripts so that infraDash can run only when data is present.

Deployment or Startup
First Time: When you deploy or start the app for the first time, you will start it using : python main.py
run_at_start.py will be executed.
run_at_start.py will check if EdgeDB.db exist. it will not exist.
run_at_start.py will then run initial_data_load.py.
initial_data_load.py will call dataRefresh2.py.
dataRefresh2.py will create EdgeDB.db and workingData.parquet.
infraDash.py can now run without issue.
Next time: when you run again python main.py
run_at_start.py will check if EdgeDB.db exist. it will exist.
run_at_start.py will not run initial_data_load.py again.
you can now run directly python infraDash.py.
"""

# streamlit run infraDash.py --server.sslCertFile localhost.crt --server.sslKeyFile localhost.key --server.address 0.0.0.0 --server.port 50000