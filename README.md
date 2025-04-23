# NeuroFeed

NeuroFeed is an intelligent RSS feed aggregator that collects news from various sources (including special handling for WeChat public accounts), processes them with AI to generate summaries, and sends personalized email digests to users. It also supports features like content filtering, scheduling, localization, and IMAP-based unsubscribe handling.

## Features

- Collect news from multiple RSS feeds, including WeChat public accounts
- AI-powered article filtering, ranking, and summarization
- Customizable email delivery scheduling
- User-friendly GUI with system tray integration
- Configurable preferences (language, AI provider, data retention, etc.)
- Support for OpenAI, local Ollama, and Silicon Flow AI models
- Automatic startup on system boot
- Localization support (English, Chinese)
- Interest tags for feed prioritization and exclusion
- IMAP integration for automatic unsubscribe request handling
- Detailed logging and cache management
- Database migration support

## Installation

```bash
# Clone the repository
git https://github.com/Arisynth/NeuroFeed
cd NeuroFeed

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp data/config.template.json data/config.json
# Edit data/config.json with your settings
```

## Usage

```bash
# Run the application
python main.py
```

## Project Structure

```
NeuroFeed/
├── main.py                 # Application entry point
├── gui/                    # GUI components
│   ├── __init__.py
│   ├── main_window.py      # Main application window
│   ├── setting_window.py   # Settings configuration window
│   ├── tray_icon.py        # System tray integration
│   ├── components/         # Reusable UI component groups
│   │   ├── __init__.py
│   │   ├── feed_manager.py
│   │   ├── recipient_manager.py
│   │   ├── scheduler_manager.py
│   │   ├── status_bar.py
│   │   └── task_manager.py
│   │   └── tag_editor.py 
│   ├── dialogs/            # Custom dialog boxes (if any)
│       └── __init__.py
|       └── feed_config_dialog.py
├── core/                   # Core business logic
│   ├── __init__.py
│   ├── config_manager.py   # Configuration loading/saving
│   ├── email_sender.py     # Email sending logic
│   ├── localization.py     # Language and translation management
│   ├── log_manager.py      # Logging setup and management
│   ├── news_db_manager.py  # Database interaction logic
│   ├── qt_init.py          # Qt environment setup
│   ├── rss_parser.py       # General RSS feed parsing
│   ├── scheduler.py        # Task scheduling and execution
│   ├── status_manager.py   # Application/task status tracking
│   ├── task_model.py       # Data model for Tasks
│   ├── task_status.py      # Enum for task statuses
│   ├── unsubscribe_handler.py # IMAP unsubscribe logic
│   ├── version.py          # Application version info
│   └── wechat_parser.py    # WeChat public account specific parsing
├── ai_processor/           # AI processing modules
│   ├── __init__.py
│   ├── filter.py           # AI content filtering
│   ├── summarizer.py       # AI article summarization
│   └── ai_utils.py         # AI service interaction utilities
├── data/                   # Data storage (created automatically)
│   ├── config.template.json # Template configuration
│   ├── rss_news.db         # SQLite database for news cache and state
│   └── logs/               # Log files directory
├── resources/              # Static application resources
│   └── icons/              # Icons for UI and tray
├── tests/                  # Unit and integration tests
│   ├── __init__.py
│   ├── test_news_db_manager.py
│   └── test_wechat_parser.py
├── utils/                  # General utility functions
│   └── resource_path.py    # Helper for finding resource paths
├── build.sh                # Build script (macOS)
├── requirements.txt        # Project dependencies
├── LICENSES_3RD_PARTY.md   # Third-party library licenses
└── README.md               # This file
```

## Configuration

The application can be configured through the settings window or by directly editing the `data/config.json` file. Log files are stored in `data/logs/`.

## Development

### Requirements

- Python 3.8 or higher
- PyQt6 for the GUI
- Key dependencies: `requests`, `beautifulsoup4`, `feedparser`, `schedule`, `pytz`, `lxml` (see `requirements.txt` for full list)
- API Keys for desired AI services (OpenAI, Silicon Flow) if not using local Ollama.

### Testing

Run tests using pytest:
```bash
pytest tests/
```
You can run specific tests, e.g., WeChat parser tests:
```bash
python tests/test_wechat_parser.py
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

