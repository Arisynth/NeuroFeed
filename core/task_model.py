class Task:
    """Represents an RSS aggregation task with its own feeds, schedule, and recipients"""
    
    def __init__(self, task_id=None, name="", rss_feeds=None, schedule=None, recipients=None, ai_settings=None):
        self.task_id = task_id
        self.name = name
        self.rss_feeds = rss_feeds or []
        self.schedule = schedule or {"type": "daily", "time": "08:00"}
        self.recipients = recipients or []
        self.ai_settings = ai_settings or {"summary_length": "medium"}
    
    def to_dict(self):
        """Convert task to dictionary for storage"""
        return {
            "id": self.task_id,
            "name": self.name,
            "rss_feeds": self.rss_feeds,
            "schedule": self.schedule,
            "recipients": self.recipients,
            "ai_settings": self.ai_settings
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a Task instance from dictionary data"""
        return cls(
            task_id=data.get("id"),
            name=data.get("name", ""),
            rss_feeds=data.get("rss_feeds", []),
            schedule=data.get("schedule", {"type": "daily", "time": "08:00"}),
            recipients=data.get("recipients", []),
            ai_settings=data.get("ai_settings", {"summary_length": "medium"})
        )
