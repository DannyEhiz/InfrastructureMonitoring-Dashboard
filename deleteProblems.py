import schedule
import time
import sqlite3
from datetime import datetime

def delete_open_problems():
    """
    Deletes all rows from the openProblems table in the EdgeDB database.
    """
    try:
        with sqlite3.connect('EdgeDB.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM openProblems")
            conn.commit()
            print(f"All rows in 'openProblems' table deleted at {datetime.now()}.")
    except sqlite3.Error as e:
        print(f"Error deleting rows from 'openProblems': {e}")

# Schedule the task to run every Sunday at midnight
schedule.every().sunday.at("00:00").do(delete_open_problems)

print("Scheduled task to delete 'openProblems' table content every Sunday at midnight.")

# Keep the script running to execute the scheduled task
while True:
    schedule.run_pending()
    time.sleep(12 * 60 * 60)  # Sleep for 12 hours to reduce resource usage
