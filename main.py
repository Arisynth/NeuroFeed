from gui.main_window import MainWindow
from core.scheduler import start_scheduler
from PyQt6.QtWidgets import QApplication
import sys

def main():
    app = QApplication(sys.argv)
    
    # Create and show the main window
    main_window = MainWindow()
    main_window.show()
    
    # Start the scheduler for periodic tasks
    start_scheduler()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()