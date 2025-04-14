import logging
import platform
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QAction, QMenu, QMenuBar

logger = logging.getLogger(__name__)

def create_exit_action(parent):
    """Create a universal exit action"""
    from PyQt6.QtGui import QIcon
    
    exit_action = QAction("Exit", parent)
    exit_action.setShortcut("Ctrl+Q")  # Standard keyboard shortcut
    exit_action.setStatusTip("Exit the application")
    exit_action.triggered.connect(force_application_exit)
    
    return exit_action

def force_application_exit():
    """Force the application to exit properly"""
    logger.info("Force exit requested via menu")
    
    # Try macOS specific exit if available
    if platform.system() == 'Darwin':
        try:
            from utils.macos_utils import force_quit_application
            if force_quit_application():
                return
        except ImportError:
            pass
    
    # Use Qt's built-in quit
    QCoreApplication.instance().quit()

def connect_menu_to_exit_action(menu, exit_action=None):
    """Connect an exit action to the given menu"""
    if exit_action is None:
        exit_action = create_exit_action(menu)
    
    # Check if menu already has an exit action
    for action in menu.actions():
        if action.text().lower() in ["exit", "quit"]:
            action.triggered.disconnect()
            action.triggered.connect(force_application_exit)
            logger.info(f"Reconnected existing exit action in {menu}")
            return action
    
    # Add new exit action if none exists
    menu.addAction(exit_action)
    logger.info(f"Added new exit action to menu")
    return exit_action
