"""
macOS specific utilities for managing dock icon visibility and application lifecycle.
Provides fallback mechanisms when PyObjC/AppKit is not available.
"""
import platform
import logging
import sys
from PyQt6.QtCore import QCoreApplication

# Configure logger
logger = logging.getLogger(__name__)

# Track dock icon state to prevent redundant operations
_dock_icon_visible = True  # Initialize to True since dock icon is visible when app starts
_app_delegate = None

def setup_macos_app():
    """Configure the macOS application with proper delegate and menu handling"""
    if platform.system() != 'Darwin':
        return False
        
    try:
        import objc
        import AppKit
        from PyQt6.QtWidgets import QApplication
        
        # Get the shared NSApplication instance
        ns_app = AppKit.NSApplication.sharedApplication()
        
        # Create a proper app menu
        menubar = AppKit.NSMenu.alloc().init()
        app_menu_item = AppKit.NSMenuItem.alloc().init()
        menubar.addItem_(app_menu_item)
        
        app_menu = AppKit.NSMenu.alloc().init()
        
        # Create Quit menu item with proper target/action
        quit_title = "Quit"
        quit_menu_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            quit_title, 'terminate:', 'q'
        )
        app_menu.addItem_(quit_menu_item)
        
        # Add menu to menubar
        app_menu_item.setSubmenu_(app_menu)
        ns_app.setMainMenu_(menubar)
        
        # Create a custom application delegate
        global _app_delegate
        
        class CustomAppDelegate(AppKit.NSObject):
            def applicationShouldTerminateAfterLastWindowClosed_(self, sender):
                return False
                
            def applicationWillTerminate_(self, notification):
                logger.info("macOS: Application will terminate")
                
            def applicationShouldTerminate_(self, sender):
                logger.info("macOS: Application should terminate")
                # Important: Schedule the app to quit properly via Qt
                QCoreApplication.instance().quit()
                return AppKit.NSTerminateCancel  # Let Qt handle the quit
                
            # Add support for dock menu
            def applicationDockMenu_(self, sender):
                dock_menu = AppKit.NSMenu.alloc().init()
                
                # Add a direct Quit item to dock menu
                quit_title = "Quit"
                quit_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    quit_title, 'terminate:', ''
                )
                dock_menu.addItem_(quit_item)
                
                return dock_menu
        
        # Create and set the delegate
        _app_delegate = CustomAppDelegate.alloc().init()
        ns_app.setDelegate_(_app_delegate)
        
        # Make app activatable
        ns_app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
        
        logger.info("macOS application customization complete")
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import required modules for macOS integration: {e}")
        return False
    except Exception as e:
        logger.error(f"Error setting up macOS application: {e}")
        return False

def show_dock_icon():
    """Show the dock icon on macOS"""
    global _dock_icon_visible
    
    if _dock_icon_visible:
        return
        
    if platform.system() != 'Darwin':
        return
        
    try:
        import objc
        import AppKit
        
        # Get the shared NSApplication instance
        app = AppKit.NSApplication.sharedApplication()
        
        # Remove the 'LSUIElement' activation policy to show the dock icon
        app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
        
        _dock_icon_visible = True
        logger.info("Dock icon shown using PyObjC/AppKit")
    except ImportError:
        logger.warning("Failed to import PyObjC/AppKit for showing dock icon")
    except Exception as e:
        logger.error(f"Error showing dock icon: {e}")

def hide_dock_icon():
    """Hide the dock icon on macOS"""
    global _dock_icon_visible
    
    if platform.system() != 'Darwin':
        return
    
    try:
        import objc
        import AppKit
        
        # Get the shared NSApplication instance
        app = AppKit.NSApplication.sharedApplication()
        
        # Set the 'LSUIElement' activation policy to hide the dock icon
        app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
        
        _dock_icon_visible = False
        logger.info("Dock icon hidden using PyObjC/AppKit")
    except ImportError:
        logger.warning("Failed to import PyObjC/AppKit for hiding dock icon")
    except Exception as e:
        logger.error(f"Error hiding dock icon: {e}")

def force_quit_application():
    """Force quit the application using macOS API"""
    if platform.system() == 'Darwin':
        try:
            import objc
            import AppKit
            logger.info("Forcing application termination via macOS API")
            AppKit.NSApplication.sharedApplication().terminate_(None)
            return True
        except Exception as e:
            logger.error(f"Failed to force quit: {e}")
    
    # Fallback to sys.exit(0)
    sys.exit(0)
    return False
