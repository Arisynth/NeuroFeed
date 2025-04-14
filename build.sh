#!/bin/bash

echo "Starting NeuroFeed build process..."

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Clean up previous build artifacts completely
echo "Cleaning previous build artifacts..."
rm -rf Release/dist Release/build Release/spec

# Create fresh output directories
mkdir -p Release/dist Release/build Release/spec

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
  --hidden-import=PyQt6 \
  --hidden-import=PyQt6.QtWidgets \
  --hidden-import=PyQt6.QtGui \
  --hidden-import=PyQt6.QtCore \
  --hidden-import=AppKit

# Check if build completed successfully
if [ $? -eq 0 ]; then
    echo "Build completed successfully!"
    
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
else
    echo "Build failed. Please check the error messages above."
    exit 1
fi
