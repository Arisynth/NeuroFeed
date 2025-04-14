import os
import sys
import gc
import logging

logger = logging.getLogger("qt_init")

def setup_qt_env():
    """
    Set up the environment for PyQt before importing any Qt modules.
    This helps prevent initialization issues and crashes.
    """
    # Increase recursion limit to avoid crashes in deep Qt object hierarchies
    sys.setrecursionlimit(5000)  # Even higher than before
    
    # Force garbage collection before Qt initialization
    gc.collect()
    
    # Set environment variables to control Qt behavior
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"  # Disable HiDPI scaling
    os.environ["QT_MAC_DISABLE_QTKIT"] = "1"       # Disable deprecated QtKit on macOS
    os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"  # Reduce Qt debug logging
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"  # Disable auto screen scaling
    
    # Disable QML JIT compilation which can cause issues
    os.environ["QML_DISABLE_DISK_CACHE"] = "1"
    
    # Disable threaded OpenGL, which can cause issues with some drivers
    os.environ["QT_OPENGL"] = "software"
    
    # Use fewer threads for rendering
    os.environ["QT_RENDER_LOOP"] = "basic"
    
    # Limit deep QtObject introspection
    os.environ["PYQT_NO_INTROSPECTION"] = "1"
    
    logger.info("Qt environment variables set")

def import_qt_modules():
    """
    Import Qt modules in a controlled way to prevent recursive import issues.
    Returns the necessary Qt modules for general use.
    """
    # Import essential modules first
    from PyQt6.QtCore import QCoreApplication, Qt, QSettings
    
    # Set application attributes before creating QApplication
    # Use try-except for each attribute since they might differ across PyQt6 versions
    try:
        # In PyQt6, this is the equivalent to disable high DPI scaling
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_Use96Dpi, True)
        logger.info("Set AA_Use96Dpi attribute")
    except (AttributeError, TypeError):
        logger.warning("AA_Use96Dpi attribute not found")
    
    try:
        # This one might still exist in PyQt6
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        logger.info("Set AA_UseHighDpiPixmaps attribute")
    except (AttributeError, TypeError):
        logger.warning("AA_UseHighDpiPixmaps attribute not found")
    
    try:
        # This one might still exist in PyQt6
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings, True)
        logger.info("Set AA_DontCreateNativeWidgetSiblings attribute")
    except (AttributeError, TypeError):
        logger.warning("AA_DontCreateNativeWidgetSiblings attribute not found")
    
    # Now import other modules in a controlled order
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont, QIcon
    
    logger.info("Qt modules imported successfully")
    
    return {
        'QApplication': QApplication,
        'QFont': QFont,
        'QIcon': QIcon,
        'Qt': Qt,
        'QSettings': QSettings
    }
