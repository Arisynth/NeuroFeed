from gui.main_window import MainWindow
from core.scheduler import start_scheduler, get_scheduler_status
from PyQt6.QtWidgets import QApplication
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

def main():
    app = QApplication(sys.argv)
    
    # Create and show the main window
    main_window = MainWindow()
    main_window.show()
    
    # Start the scheduler for periodic tasks
    logger.info("Starting scheduler...")
    scheduler_thread = start_scheduler()
    
    # Verify scheduler status
    if scheduler_thread and scheduler_thread.is_alive():
        logger.info("Scheduler thread is running")
        
        # Get and log scheduled tasks
        status = get_scheduler_status()
        logger.info(f"Active scheduled jobs: {status['active_jobs']}")
        
        if status['next_jobs']:
            logger.info("Upcoming scheduled tasks:")
            for job in status['next_jobs']:
                logger.info(f"- {job['time']} ({job['minutes_from_now']} minutes from now)")
        else:
            logger.info("No upcoming scheduled tasks in the next 24 hours")
    else:
        logger.warning("Scheduler thread may not be running properly")
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()