import sys
import platform

def hide_dock_icon():
    """Hide the application from the macOS Dock"""
    if platform.system() == 'Darwin':  # macOS
        try:
            from AppKit import NSApp, NSApplicationActivationPolicyAccessory
            NSApp().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
            return True
        except ImportError:
            print("AppKit not available - are you using PyQt on macOS without PyObjC?")
            return False
    return False

def show_dock_icon():
    """Show the application in the macOS Dock"""
    if platform.system() == 'Darwin':  # macOS
        try:
            from AppKit import NSApp, NSApplicationActivationPolicyRegular
            NSApp().setActivationPolicy_(NSApplicationActivationPolicyRegular)
            return True
        except ImportError:
            print("AppKit not available - are you using PyQt on macOS without PyObjC?")
            return False
    return False
