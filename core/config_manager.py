import json
import os
import uuid

CONFIG_PATH = "data/config.json"

def load_config():
    try:
        if os.path.exists(CONFIG_PATH) and os.path.getsize(CONFIG_PATH) > 0:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        # Return default config with tasks array and global settings
        return {
            "tasks": [], 
            "global_settings": {
                "email_settings": {},
                "ai_settings": {"provider": "ollama"},
                "general_settings": {"minimize_to_tray": True}
            }
        }
    except json.JSONDecodeError:
        # If the file contains invalid JSON, return empty dict
        print(f"Warning: Config file at {CONFIG_PATH} contains invalid JSON. Using default configuration.")
        return {
            "tasks": [], 
            "global_settings": {
                "email_settings": {},
                "ai_settings": {"provider": "ollama"},
                "general_settings": {"minimize_to_tray": True}
            }
        }

def save_config(config):
    # Ensure the directory exists
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def get_tasks():
    """Get list of all tasks from config"""
    config = load_config()
    from core.task_model import Task
    return [Task.from_dict(task_dict) for task_dict in config.get("tasks", [])]

def save_task(task):
    """Save a task to config"""
    config = load_config()
    
    # Generate ID if new task
    if not task.task_id:
        task.task_id = str(uuid.uuid4())
    
    # Update or add task
    tasks = config.get("tasks", [])
    updated = False
    
    for i, existing_task in enumerate(tasks):
        if existing_task.get("id") == task.task_id:
            tasks[i] = task.to_dict()
            updated = True
            break
    
    if not updated:
        tasks.append(task.to_dict())
    
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
        config["global_settings"]["general_settings"][key] = value
    
    # 输出调试信息，确认设置已更新
    print(f"更新后的通用设置: {config['global_settings']['general_settings']}")
    
    # 保存更新后的配置
    save_config(config)
    return True