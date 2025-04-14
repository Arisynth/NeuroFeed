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
        echo "App signed successfully. Ready for limited distribution."
        echo "The app is located in Release/dist folder."
    else
        echo "Warning: App signing failed. The app will still work but may trigger security warnings."
    fi
else
    echo "Build failed. Please check the error messages above."
    exit 1
fi
