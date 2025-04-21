import sys
import logging
import faulthandler
import platform
import os
import gc

# Enable faulthandler to get better crash reports
faulthandler.enable()

# Setup logging early, before any imports
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

# Import and use our Qt initialization module
from core.qt_init import setup_qt_env, import_qt_modules

# Set up the Qt environment before any PyQt imports
setup_qt_env()

# Import modules in controlled order after environment is set up
qt_modules = import_qt_modules()
QApplication = qt_modules['QApplication']
Qt = qt_modules['Qt']

# Now safe to import the rest
from gui.main_window import MainWindow
from core.scheduler import start_scheduler, get_scheduler_status
from core.unsubscribe_handler import trigger_unsubscribe_check # Import the trigger function

def main():
    # Create application instance
    app = QApplication(sys.argv)
    
    # Configure application shutdown behavior
    app.setQuitOnLastWindowClosed(False)
    
    # Set up macOS specific handling
    if platform.system() == 'Darwin':
        try:
            from utils.macos_utils import setup_macos_app
            if setup_macos_app():
                logger.info("macOS app customization successful")
            else:
                logger.warning("macOS app customization failed, using fallback")
        except ImportError:
            logger.warning("Could not import macOS utilities, using standard configuration")
    
    # Ensure app can exit properly when quit is requested
    app.aboutToQuit.connect(lambda: logger.info("Application is about to quit"))
    
    # Create main window
    logger.info("Creating main window...")
    main_window = MainWindow()
    main_window.show()
    
    # Start the scheduler for periodic tasks after UI is initialized
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
    
    # --- Temporary Test Trigger ---
    # Call this to manually start the unsubscribe check for testing
    # Remember to remove this line after testing
    logger.info("TEMPORARY: Triggering manual unsubscribe check for testing...")
    trigger_unsubscribe_check()
    # --- End Temporary Test Trigger ---

    # Run the application event loop
    exit_code = app.exec()
    
    # Clean up resources before exit
    logger.info(f"Application exiting with code {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()