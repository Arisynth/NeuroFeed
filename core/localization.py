"""
Localization module for multi-language support
"""

from core.config_manager import get_general_settings

# Default language is English
_current_language = "en"

# Translations dictionary
_translations = {
    # English translations
    "en": {
        # General UI elements
        "settings": "Settings",
        "save": "Save",
        "close": "Close",
        "cancel": "Cancel",
        "ok": "OK",
        "error": "Error",
        "warning": "Warning",
        "info": "Information",
        
        # Email related
        "email_settings": "Email Settings",
        "test_email": "Test Email Settings",
        "smtp_server": "SMTP Server",
        "port": "Port",
        "security": "Security",
        "sender_email": "Sender Email",
        "password": "Password",
        "remember_password": "Remember password",
        
        # AI settings
        "ai_settings": "AI Settings",
        "ai_provider": "AI Provider",
        "model": "Model",
        "api_key": "API Key",
        
        # General settings
        "general_settings": "General Settings",
        "app_behavior": "Application Behavior",
        "start_on_boot": "Start application on system startup",
        "minimize_to_tray": "Minimize to system tray when closed",
        "show_notifications": "Show notifications",
        "skip_processed": "Skip processed news articles (test feature)",
        "language": "Language",
        
        # Data management
        "data_management": "Data Management",
        "clear_cache": "Clear RSS News Cache",
        "clear_cache_desc": "Click the button to clear the cache of processed news, ensuring all RSS sources will be retrieved and processed again on next run",
        
        # Interest tags
        "interest_tags": "Interest Tags",
        "set_interests": "Set your interest tags that will be automatically applied when adding new RSS feeds",
        
        # Scheduler
        "schedule_settings": "Schedule Settings",
        "frequency": "Frequency",
        "time": "Time",
        "run_on_days": "Run on these days",
        "weekdays": "Weekdays",
        "weekends": "Weekends",
        "all_days": "All Days",
        "none": "None",
        "last_run": "Last run",
        "next_run": "Next run",
        "never": "Never",
        "not_scheduled": "Not scheduled",
        
        # Messages
        "settings_saved": "Settings saved!",
        "restart_required": "The language setting has been changed. Please restart the application for the changes to take effect.",
        
        # MainWindow
        "rss_feeds": "RSS Feeds",
        "schedule": "Schedule",
        "recipients": "Recipients",
        "run_now": "Run Now",
        "running": "Running...",
        "no_task": "No Task",
        "no_task_selected": "No task selected or available.",
        "task_started": "Task Started",
        "task_started_message": "The task",
        "task_started_note": "This may take some time, especially if using AI filtering.\nYou can continue using the application while the task runs.",
        "task_error": "Task Error",
        "error_starting_task": "Error starting task",
        "schedule_updated": "Schedule Updated",
        "schedule_updated_message": "The schedule has been updated.",
        "tasks_scheduled": "task(s) have been scheduled.",
        "schedule_error": "Schedule Error",
        "error_reloading_tasks": "Error reloading tasks",
        "settings_error": "Settings Error",
        "error_opening_settings": "Error opening settings",
        
        # Settings Window
        "email": "Email",
        "smtp_server_settings": "SMTP Server Settings",
        "authentication_settings": "Authentication Settings",
        "ollama_settings": "Ollama Settings",
        "openai_settings": "OpenAI Settings",
        "ollama_host": "Ollama Host",
        "refresh": "Refresh",
        "general": "General",
        "test_feature": "Test Feature",
        "skip_processed_tooltip": "When enabled, the system will skip already processed news articles to avoid duplicate processing",
        "clear_cache_tooltip": "Clear all RSS news data stored in the database to retrieve and process feeds from scratch",
        "unsaved_changes": "Unsaved Changes",
        "save_changes_prompt": "You have unsaved changes. Do you want to save before closing?",
        "incomplete_info": "Incomplete Information",
        "fill_email_settings": "Please fill in all email settings (server, email, and password).",
        "sending_test": "Sending Test",
        "sending_test_to": "Sending test email to",
        "please_wait": "Please wait...",
        "success": "Success",
        "test_email_sent": "Test email sent successfully!",
        "failed": "Failed",
        "test_email_failed": "Failed to send test email.",
        "settings_effect_next_run": "New article processing settings will take effect on the next task run!",
    },
    
    # Chinese translations
    "zh": {
        # General UI elements
        "settings": "设置",
        "save": "保存",
        "close": "关闭",
        "cancel": "取消",
        "ok": "确定",
        "error": "错误",
        "warning": "警告",
        "info": "信息",
        
        # Email related
        "email_settings": "邮箱设置",
        "test_email": "测试邮箱设置",
        "smtp_server": "SMTP服务器",
        "port": "端口",
        "security": "安全类型",
        "sender_email": "发件人邮箱",
        "password": "密码",
        "remember_password": "记住密码",
        
        # AI settings
        "ai_settings": "AI设置",
        "ai_provider": "AI提供商",
        "model": "模型",
        "api_key": "API密钥",
        
        # General settings
        "general_settings": "常规设置",
        "app_behavior": "应用程序行为",
        "start_on_boot": "系统启动时运行应用程序",
        "minimize_to_tray": "关闭时最小化到系统托盘",
        "show_notifications": "显示通知",
        "skip_processed": "跳过已处理的新闻文章（测试功能）",
        "language": "语言",
        
        # Data management
        "data_management": "数据管理",
        "clear_cache": "清除RSS新闻缓存",
        "clear_cache_desc": "点击按钮清除已处理的新闻缓存，确保下次运行时重新获取和处理所有RSS源",
        
        # Interest tags
        "interest_tags": "兴趣标签",
        "set_interests": "设置您的兴趣标签，添加新RSS源时将自动应用",
        
        # Scheduler
        "schedule_settings": "调度设置",
        "frequency": "频率",
        "time": "时间",
        "run_on_days": "在这些日子运行",
        "weekdays": "工作日",
        "weekends": "周末",
        "all_days": "所有日子",
        "none": "无",
        "last_run": "上次运行",
        "next_run": "下次运行",
        "never": "从未",
        "not_scheduled": "未调度",
        
        # Messages
        "settings_saved": "设置已保存！",
        "restart_required": "语言设置已更改。请重新启动应用程序以使更改生效。",
        
        # MainWindow
        "rss_feeds": "RSS源",
        "schedule": "调度",
        "recipients": "接收者",
        "run_now": "立即运行",
        "running": "正在运行...",
        "no_task": "无任务",
        "no_task_selected": "没有选择或可用的任务。",
        "task_started": "任务已启动",
        "task_started_message": "任务",
        "task_started_note": "这可能需要一些时间，特别是使用AI过滤时。\n您可以在任务运行时继续使用应用程序。",
        "task_error": "任务错误",
        "error_starting_task": "启动任务出错",
        "schedule_updated": "调度已更新",
        "schedule_updated_message": "调度已更新。",
        "tasks_scheduled": "个任务已被调度。",
        "schedule_error": "调度错误",
        "error_reloading_tasks": "重新加载任务出错",
        "settings_error": "设置错误",
        "error_opening_settings": "打开设置出错",
        
        # Settings Window
        "email": "邮箱",
        "smtp_server_settings": "SMTP服务器设置",
        "authentication_settings": "认证设置",
        "ollama_settings": "Ollama设置",
        "openai_settings": "OpenAI设置",
        "ollama_host": "Ollama主机",
        "refresh": "刷新",
        "general": "常规",
        "test_feature": "测试功能",
        "skip_processed_tooltip": "启用后，系统将跳过已处理过的新闻文章，避免重复处理",
        "clear_cache_tooltip": "清除数据库中存储的所有RSS新闻数据，以便重新获取和处理",
        "unsaved_changes": "未保存的更改",
        "save_changes_prompt": "您有未保存的更改。是否在关闭前保存？",
        "incomplete_info": "信息不完整",
        "fill_email_settings": "请填写所有邮箱设置（服务器、邮箱和密码）。",
        "sending_test": "发送测试",
        "sending_test_to": "正在发送测试邮件到",
        "please_wait": "请稍候...",
        "success": "成功",
        "test_email_sent": "测试邮件发送成功！",
        "failed": "失败",
        "test_email_failed": "发送测试邮件失败。",
        "settings_effect_next_run": "新的文章处理设置将在下次运行任务时生效！",
    }
}

def initialize():
    """Initialize localization system by loading current language from settings"""
    global _current_language
    settings = get_general_settings()
    _current_language = settings.get("language", "en")
    print(f"Localization initialized with language: {_current_language}")

def get_text(key):
    """Get translated text for the given key"""
    try:
        return _translations[_current_language].get(key, key)
    except KeyError:
        # Fallback to English if the language is not available
        try:
            return _translations["en"].get(key, key)
        except KeyError:
            # Return the key itself if it's not found in any language
            return key

def get_current_language():
    """Get the current language code"""
    return _current_language

def set_language(language_code):
    """Set the current language"""
    global _current_language
    if language_code in _translations:
        _current_language = language_code
        return True
    return False

# Helper function for text with parameters
def get_formatted(key, *args, **kwargs):
    """Get translated text and format it with the given parameters"""
    text = get_text(key)
    try:
        if args or kwargs:
            return text.format(*args, **kwargs)
        return text
    except Exception:
        # If formatting fails, return the unformatted text
        return text
