"""
macOS specific utilities for managing dock icon visibility.
Provides fallback mechanisms when PyObjC/AppKit is not available.
"""
import platform
import logging
import subprocess
import os
import sys

# Configure logger
logger = logging.getLogger(__name__)

# Check if we're on macOS
IS_MACOS = platform.system() == 'Darwin'

# Flag to track if we're using PyObjC or fallback methods
using_pyobjc = False
using_fallback = False

# First attempt: Try to use PyObjC/AppKit directly
if IS_MACOS:
    try:
        import objc
        from Foundation import NSBundle
        from AppKit import NSApp, NSApplicationActivationPolicyRegular, NSApplicationActivationPolicyAccessory
        
        # Mark that we're using PyObjC
        using_pyobjc = True
        logger.info("Successfully loaded PyObjC/AppKit for dock icon management")
    except ImportError as e:
        logger.warning(f"PyObjC/AppKit not available: {e} - will try fallback methods")
        using_pyobjc = False

def _run_osascript(script):
    """Run an AppleScript command using osascript"""
    if not IS_MACOS:
        logger.warning("Attempted to run AppleScript on non-macOS platform")
        return False
    
    try:
        subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to run AppleScript: {e}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr.decode('utf-8')}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error running AppleScript: {e}")
        return False

def hide_dock_icon():
    """Hide the app icon from the dock"""
    if not IS_MACOS:
        logger.info("Not on macOS - dock icon functions are no-ops")
        return
    
    # Method 1: Use PyObjC/AppKit if available
    if using_pyobjc:
        try:
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
            logger.info("Dock icon hidden using PyObjC/AppKit")
            return
        except Exception as e:
            logger.error(f"Failed to hide dock icon with PyObjC: {e} - trying fallback")
    
    # Method 2: Use AppleScript as fallback
    app_name = os.path.basename(sys.executable)
    if _run_osascript(f'tell application "System Events" to set visible of process "{app_name}" to false'):
        logger.info(f"Dock icon hidden using AppleScript fallback for {app_name}")
    else:
        logger.warning("Failed to hide dock icon using all available methods")

def show_dock_icon():
    """Show the app icon in the dock"""
    if not IS_MACOS:
        logger.info("Not on macOS - dock icon functions are no-ops")
        return
    
    # Method 1: Use PyObjC/AppKit if available
    if using_pyobjc:
        try:
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
            logger.info("Dock icon shown using PyObjC/AppKit")
            return
        except Exception as e:
            logger.error(f"Failed to show dock icon with PyObjC: {e} - trying fallback")
    
    # Method 2: Use AppleScript as fallback
    app_name = os.path.basename(sys.executable)
    if _run_osascript(f'tell application "System Events" to set visible of process "{app_name}" to true'):
        logger.info(f"Dock icon shown using AppleScript fallback for {app_name}")
    else:
        logger.warning("Failed to show dock icon using all available methods")
