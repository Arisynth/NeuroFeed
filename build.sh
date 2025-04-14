#!/bin/bash

echo "Starting NeuroFeed build process..."

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Clean up previous build artifacts completely
echo "Cleaning previous build artifacts..."
rm -rf Release/dist Release/build Release/spec

# Create fresh output directories
mkdir -p Release/dist Release/build Release/spec

# Generate additional imports list for PyInstaller to handle all GUI modules
echo "Creating comprehensive imports list for PyInstaller..."
cat > pyinstaller-imports.py << EOF
# This script is used to generate imports for PyInstaller
import PyQt6
import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtWidgets
import PyQt6.QtDBus
import PyQt6.QtNetwork
import PyQt6.QtSvg
import PyQt6.sip
import sys
import sip
import gc
import objc
import AppKit
import Foundation
import sys
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
print("All modules imported successfully.")
EOF

# Run the import script to verify modules are available
python3 pyinstaller-imports.py

# Build directly with the known working configuration
echo "Running PyInstaller with --onedir..."
pyinstaller main.py \
  --name NeuroFeedApp \
  --onedir \
  --windowed \
  --noconfirm \
  --clean \
  --icon="${PROJECT_DIR}/resources/icon.icns" \
  --add-data "${PROJECT_DIR}/resources/icon.png:resources" \
  --add-data "${PROJECT_DIR}/data/config.template.json:data" \
  --distpath Release/dist \
  --workpath Release/build \
  --specpath Release/spec \
  --exclude-module PyQt6.Qt6.QtBluetooth \
  --paths=venv/lib/python3.12/site-packages \
  --hidden-import=core.qt_init \
  --hidden-import=PyQt6 \
  --hidden-import=PyQt6.QtWidgets \
  --hidden-import=PyQt6.QtGui \
  --hidden-import=PyQt6.QtCore \
  --hidden-import=PyQt6.sip \
  --hidden-import=PyQt6.QtDBus \
  --hidden-import=PyQt6.QtNetwork \
  --hidden-import=PyQt6.QtSvg \
  --hidden-import=AppKit \
  --hidden-import=gc \
  --hidden-import=objc \
  --hidden-import=sip \
  --hidden-import=Foundation

# Check if build completed successfully
if [ $? -eq 0 ]; then
    echo "Build completed successfully!"
    
    # Add info.plist customization to set larger stack size
    PLIST_FILE="Release/dist/NeuroFeedApp.app/Contents/Info.plist"
    if [ -f "$PLIST_FILE" ]; then
        echo "Updating Info.plist with custom settings..."
        
        # Add stack size values - increasing even more from previous value
        /usr/libexec/PlistBuddy -c "Add :NSMainThreadStackSize integer 16777216" "$PLIST_FILE" 2>/dev/null || \
        /usr/libexec/PlistBuddy -c "Set :NSMainThreadStackSize 16777216" "$PLIST_FILE"
        
        # Add high memory mode flag
        /usr/libexec/PlistBuddy -c "Add :NSHighResolutionCapable bool true" "$PLIST_FILE" 2>/dev/null || \
        /usr/libexec/PlistBuddy -c "Set :NSHighResolutionCapable true" "$PLIST_FILE"
        
        # Add app category
        /usr/libexec/PlistBuddy -c "Add :LSApplicationCategoryType string public.app-category.productivity" "$PLIST_FILE" 2>/dev/null || \
        /usr/libexec/PlistBuddy -c "Set :LSApplicationCategoryType public.app-category.productivity" "$PLIST_FILE"
    fi
    
    # Ad-hoc signing for limited distribution
    echo "Performing ad-hoc signing..."
    codesign --deep --force --sign - "Release/dist/NeuroFeedApp.app"
    
    if [ $? -eq 0 ]; then
        echo "App signed successfully."
        
        # Create disk image for easy distribution
        echo "Creating disk image for distribution..."
        hdiutil create -volname "NeuroFeedApp" -srcfolder "Release/dist/NeuroFeedApp.app" -ov -format UDZO "Release/dist/NeuroFeedApp.dmg"
        
        if [ $? -eq 0 ]; then
            echo "Disk image created successfully at Release/dist/NeuroFeedApp.dmg"
            echo ""
            echo "=================================================="
            echo "IMPORTANT INSTRUCTIONS FOR RECIPIENTS:"
            echo "=================================================="
            echo "When opening the app for the first time:"
            echo "1. Right-click (or Control+click) on the app"
            echo "2. Select 'Open' from the menu"
            echo "3. Click 'Open' in the dialog that appears"
            echo ""
            echo "Alternatively, they can run this in Terminal:"
            echo "sudo xattr -rd com.apple.quarantine /path/to/NeuroFeedApp.app"
            echo "=================================================="
        else
            echo "Failed to create disk image."
        fi
    else
        echo "Warning: App signing failed. The app will trigger security warnings."
    fi
    
    # Clean up temporary files
    rm -f pyinstaller-imports.py
else
    echo "Build failed. Please check the error messages above."
    exit 1
fi
