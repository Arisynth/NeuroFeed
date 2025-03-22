import json
import os
import uuid

CONFIG_PATH = "data/config.json"

def load_config():
    try:
        if os.path.exists(CONFIG_PATH) and os.path.getsize(CONFIG_PATH) > 0:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        # Return default config with tasks array
        return {"tasks": [], "global_settings": {}}
    except json.JSONDecodeError:
        # If the file contains invalid JSON, return empty dict
        print(f"Warning: Config file at {CONFIG_PATH} contains invalid JSON. Using default configuration.")
        return {"tasks": [], "global_settings": {}}

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