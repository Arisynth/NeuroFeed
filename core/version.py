"""
Version information for NeuroFeed.
This file is used to store and manage version information across the application.
"""

# Version components
MAJOR = 1
MINOR = 1
PATCH = 1

# Build version string
VERSION = f"{MAJOR}.{MINOR}.{PATCH}"

# Additional version details
BUILD_DATE = None  # Can be set during build process
COMMIT_HASH = None  # Can be populated during CI/CD

def get_version_string(include_build_info=False):
    """Return the formatted version string."""
    version_str = VERSION
    
    if include_build_info and (BUILD_DATE or COMMIT_HASH):
        build_info = []
        if BUILD_DATE:
            build_info.append(f"build:{BUILD_DATE}")
        if COMMIT_HASH:
            build_info.append(f"commit:{COMMIT_HASH}")
            
        version_str = f"{version_str} ({', '.join(build_info)})"
        
    return version_str
