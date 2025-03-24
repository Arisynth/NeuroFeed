# NeuroFeed

NeuroFeed is an intelligent RSS feed aggregator that collects news from various sources, processes them with AI to generate summaries, and sends personalized email digests to users. SmartDigest is a feature within NeuroFeed that handles the content filtering and summarization.

## Features

- Collect news from multiple RSS feeds
- AI-powered article filtering, ranking, and summarization
- Customizable email delivery scheduling
- User-friendly GUI with system tray integration
- Configurable preferences
- Support for both OpenAI and local Ollama models
- Automatic startup on system boot

## Installation

```bash
# Clone the repository
git clone https://github.com/iasonyc/NeuroFeed.git
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
│   ├── __init__.py         # Package initialization
│   ├── main_window.py      # Main application window
│   ├── setting_window.py   # Settings configuration window
│   ├── tray_icon.py        # System tray integration
├── core/                   # Core business logic
│   ├── __init__.py         # Package initialization
│   ├── rss_parser.py       # RSS feed parser
│   ├── email_sender.py     # Email delivery system
│   ├── scheduler.py        # Task scheduling
│   ├── config_manager.py   # Configuration management
├── ai_processor/           # AI processing modules
│   ├── __init__.py         # Package initialization
│   ├── filter.py           # Content filtering
│   ├── summarizer.py       # Article summarization
│   ├── ai_utils.py         # AI utilities (GPT/Ollama API)
├── data/                   # Data storage
│   ├── config.json         # User configuration
│   ├── rss_feeds.db        # SQLite database for RSS feeds
├── resources/              # Application resources
│   ├── icons/              # System tray and UI icons
│   ├── styles.qss          # Qt stylesheet for UI
└── requirements.txt        # Project dependencies
```

## Configuration

The application can be configured through the settings window or by directly editing the `data/config.json` file.

## Development

### Requirements

- Python 3.8 or higher
- PyQt6 for the GUI
- Dependencies listed in requirements.txt

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

