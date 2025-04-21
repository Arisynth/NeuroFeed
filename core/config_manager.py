import json
import os
import uuid
import shutil
import logging
from core.version import VERSION, get_version_string

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
TEMPLATE_PATH = os.path.join(CONFIG_DIR, "config.template.json")

# Add version to the exported variables
__version__ = VERSION

def initialize_config():
    """Initialize the configuration file if it doesn't exist"""
    # Create config directory if it doesn't exist
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
        logger.info(f"Created configuration directory: {CONFIG_DIR}")
        
    # Check if config file exists
    if not os.path.exists(CONFIG_PATH):
        if os.path.exists(TEMPLATE_PATH):
            # Load template to mark example tasks
            try:
                with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
                    template_config = json.load(f)
                    # Mark all template tasks as examples
                    for task in template_config.get("tasks", []):
                        task["is_template"] = True
                        # Ensure each template task has an ID for later identification
                        if "id" not in task:
                            task["id"] = str(uuid.uuid4())
                
                # Save the modified template as the config
                with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                    json.dump(template_config, f, indent=4, ensure_ascii=False)
                logger.info(f"Created initial configuration from template with marked example tasks")
            except Exception as e:
                logger.error(f"Error processing template: {e}")
                # Fallback to direct copy if processing fails
                shutil.copy(TEMPLATE_PATH, CONFIG_PATH)
                logger.info(f"Created initial configuration from template (direct copy)")
        else:
            # Create a minimal default config
            default_config = {
                "tasks": [],
                "global_settings": {
                    "email_settings": {
                        "smtp_server": "",
                        "smtp_port": 465,
                        "smtp_security": "SSL/TLS",
                        "sender_email": "",
                        "email_password": "",
                        "remember_password": False,
                        "imap_settings": {  # Add IMAP defaults
                            "server": "",
                            "port": 993,
                            "security": "SSL/TLS",
                            "username": "",
                            "password": ""
                        }
                    },
                    "ai_settings": {
                        "provider": "ollama",
                        "ollama_host": "http://localhost:11434",
                        "ollama_model": "model-name",
                        "openai_model": "gpt-3.5-turbo",
                        "siliconflow_model": "Qwen/Qwen2-7B-Instruct"
                    },
                    "general_settings": {
                        "start_on_boot": True,
                        "minimize_to_tray": True,
                        "show_notifications": True,
                        "skip_processed_articles": True,
                        "language": "en",
                        "db_retention_days": 30
                    },
                    "user_interests": [],
                    "user_negative_interests": []
                }
            }
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            logger.info(f"Created default configuration file")

def load_config():
    """Load configuration from file, initializing if necessary"""
    initialize_config()
    
    # Define a complete default configuration structure
    default_config = {
        "tasks": [], 
        "global_settings": {
            "email_settings": {
                "smtp_server": "",
                "smtp_port": 465,
                "smtp_security": "SSL/TLS",
                "sender_email": "",
                "email_password": "",
                "remember_password": False,
                "imap_settings": {  # Add IMAP defaults
                    "server": "",
                    "port": 993,
                    "security": "SSL/TLS",
                    "username": "",
                    "password": ""
                }
            },
            "ai_settings": {
                "provider": "ollama",
                "ollama_host": "http://localhost:11434",
                "ollama_model": "model-name",
                "openai_model": "gpt-3.5-turbo",
                "siliconflow_model": "Qwen/Qwen2-7B-Instruct"
            },
            "general_settings": {
                "start_on_boot": True,
                "minimize_to_tray": True,
                "show_notifications": True,
                "skip_processed_articles": False,
                "language": "en",
                "db_retention_days": 30
            },
            "user_interests": [],
            "user_negative_interests": []
        }
    }
    
    try:
        if os.path.exists(CONFIG_PATH) and os.path.getsize(CONFIG_PATH) > 0:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)
                
                # Ensure the loaded config has all necessary nested structures
                if "tasks" not in loaded_config:
                    loaded_config["tasks"] = default_config["tasks"]
                
                if "global_settings" not in loaded_config:
                    loaded_config["global_settings"] = default_config["global_settings"]
                else:
                    # Ensure all nested settings are present
                    for key, value in default_config["global_settings"].items():
                        if key not in loaded_config["global_settings"]:
                            loaded_config["global_settings"][key] = value
                        elif isinstance(value, dict) and isinstance(loaded_config["global_settings"][key], dict):
                            # For nested dictionaries, ensure all keys exist
                            for sub_key, sub_value in value.items():
                                if sub_key not in loaded_config["global_settings"][key]:
                                    loaded_config["global_settings"][key][sub_key] = sub_value
                                # Ensure IMAP settings structure exists and is complete
                                elif key == "email_settings" and sub_key == "imap_settings" and isinstance(sub_value, dict):
                                    if "imap_settings" not in loaded_config["global_settings"]["email_settings"]:
                                        loaded_config["global_settings"]["email_settings"]["imap_settings"] = sub_value
                                    elif isinstance(loaded_config["global_settings"]["email_settings"]["imap_settings"], dict):
                                        # Remove check_interval_minutes if it exists from old configs
                                        loaded_config["global_settings"]["email_settings"]["imap_settings"].pop("check_interval_minutes", None)
                                        for imap_key, imap_default in sub_value.items():
                                            if imap_key not in loaded_config["global_settings"]["email_settings"]["imap_settings"]:
                                                loaded_config["global_settings"]["email_settings"]["imap_settings"][imap_key] = imap_default
                                    else: # If imap_settings exists but is not a dict, replace it
                                        loaded_config["global_settings"]["email_settings"]["imap_settings"] = sub_value
                                        # Ensure interval is removed if replaced
                                        loaded_config["global_settings"]["email_settings"]["imap_settings"].pop("check_interval_minutes", None)

                return loaded_config
        
        # If file doesn't exist or is empty, return the default config
        return default_config
    except json.JSONDecodeError:
        # If the file contains invalid JSON, log warning and return default config
        logger.warning(f"Config file at {CONFIG_PATH} contains invalid JSON. Using default configuration.")
        return default_config

def save_config(config):
    """Save configuration to file with proper synchronization"""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    
    # Create temp file first to ensure atomic write
    temp_path = CONFIG_PATH + '.tmp'
    
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
            f.flush()  # Make sure data is written to disk
            os.fsync(f.fileno())  # Force OS to write to disk
        
        # Rename is atomic on most systems
        if os.path.exists(CONFIG_PATH):
            os.replace(temp_path, CONFIG_PATH)  # Atomic replacement
        else:
            os.rename(temp_path, CONFIG_PATH)
            
        # Additional debug to confirm save happened
        logger.debug(f"Config saved successfully to {CONFIG_PATH}")
        
        # Return a simple check that config was saved
        return os.path.exists(CONFIG_PATH) and os.path.getsize(CONFIG_PATH) > 0
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass
        return False

def get_tasks():
    """Get list of all tasks from config"""
    config = load_config()
    from core.task_model import Task
    tasks = []
    for task_dict in config.get("tasks", []):
        task = Task.from_dict(task_dict)
        # If this is a template task, mark it for the UI
        if task_dict.get("is_template", False):
            task.is_template = True
        tasks.append(task)
    return tasks

def save_task(task):
    """Save a task to config"""
    config = load_config()
    
    # Generate ID if new task
    if not task.task_id:
        task.task_id = str(uuid.uuid4())
    
    # Update or add task
    tasks = config.get("tasks", [])
    updated = False
    
    # First, check if this is a modified template task
    template_task_idx = None
    for i, existing_task in enumerate(tasks):
        # If this task came from a template task that's being edited
        if task.derived_from_template_id and existing_task.get("id") == task.derived_from_template_id:
            template_task_idx = i
        
        # Regular task update check
        if existing_task.get("id") == task.task_id:
            tasks[i] = task.to_dict()
            # Make sure we're not marking non-template tasks as templates
            if "is_template" in tasks[i] and not task.is_template:
                del tasks[i]["is_template"]
            updated = True
            break
    
    # If we found a template task that was modified, remove it
    if template_task_idx is not None and not updated:
        logger.info(f"Removing template task that was modified")
        # Remove template task
        del tasks[template_task_idx]
    
    # Add task if not an update
    if not updated:
        task_dict = task.to_dict()
        # Ensure we're not carrying over the derived_from_template_id field
        if hasattr(task, 'derived_from_template_id'):
            task_dict.pop('derived_from_template_id', None)
        tasks.append(task_dict)
    
    config["tasks"] = tasks
    save_config(config)
    return task

def delete_task(task_id):
    """Delete a task from config"""
    config = load_config()
    config["tasks"] = [t for t in config.get("tasks", []) if t.get("id") != task_id]
    save_config(config)

def get_general_settings():
    """获取通用设置"""
    config = load_config()
    
    # 确保路径存在并访问正确的嵌套结构
    if "global_settings" not in config:
        config["global_settings"] = {}
    
    if "general_settings" not in config["global_settings"]:
        config["global_settings"]["general_settings"] = {}
    
    general_settings = config["global_settings"]["general_settings"]
    
    # 确保所有必要的设置都有默认值
    if "skip_processed_articles" not in general_settings:
        general_settings["skip_processed_articles"] = False
    
    # 更新配置文件确保所有新增的默认值都保存了
    save_config(config)
    
    return general_settings

def update_general_settings(settings):
    """更新通用设置"""
    config = load_config()
    
    # 确保global_settings存在
    if "global_settings" not in config:
        config["global_settings"] = {}
    
    # 确保general_settings存在
    if "general_settings" not in config["global_settings"]:
        config["global_settings"]["general_settings"] = {}
    
    # 更新设置
    for key, value in settings.items():
        # 确保明确设置语言，不让它被忽略
        if key == "language":
            logger.debug(f"Explicitly setting language to: {value}")
        
        config["global_settings"]["general_settings"][key] = value
    
    # 如果更改了开机自启动设置，则需要实际应用该设置
    if "start_on_boot" in settings:
        try:
            from core.autostart import enable_autostart, disable_autostart
            if settings["start_on_boot"]:
                enable_autostart()
            else:
                disable_autostart()
        except Exception as e:
            logger.error(f"应用开机自启动设置时出错: {str(e)}")
    
    # 输出调试信息，确认设置已更新
    logger.debug(f"更新后的通用设置: {config['global_settings']['general_settings']}")
    print(f"更新后的通用设置: {config['global_settings']['general_settings']}")
    
    # 保存更新后的配置
    success = save_config(config)
    
    # Verify language was saved correctly
    if "language" in settings:
        # Force reload from disk to verify
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved_config = json.load(f)
                saved_language = saved_config.get("global_settings", {}).get("general_settings", {}).get("language")
                logger.debug(f"Verification - Direct file read, language: {saved_language}")
                if saved_language != settings["language"]:
                    logger.error(f"Language setting discrepancy! Expected {settings['language']} but got {saved_language}")
        except Exception as e:
            logger.error(f"Error verifying config: {e}")
            
    return success

def get_app_version(include_build_info=False):
    """Return the application version string."""
    return get_version_string(include_build_info)