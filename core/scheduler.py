import schedule
import time
import threading

def test_job():
    print("🕒 Running scheduled task...")

def start_scheduler():
    schedule.every(10).seconds.do(test_job)

    def run_loop():
        while True:
            schedule.run_pending()
            time.sleep(1)

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()