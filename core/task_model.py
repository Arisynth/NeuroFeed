from datetime import datetime

class Task:
    """Represents an RSS aggregation task with its own feeds, schedule, and recipients"""
    
    def __init__(self, task_id=None, name="", rss_feeds=None, schedule=None, recipients=None, ai_settings=None,
                 feeds_status=None, recipients_status=None, last_run=None):
        self.task_id = task_id
        self.name = name
        self.rss_feeds = rss_feeds or []
        self.schedule = schedule or {"type": "daily", "time": "08:00"}
        self.recipients = recipients or []
        self.ai_settings = ai_settings or {"summary_length": "medium"}
        
        # Status tracking for feeds and recipients
        self.feeds_status = feeds_status or {}  # Format: {"feed_url": {"status": "success/fail", "last_fetch": "timestamp"}}
        self.recipients_status = recipients_status or {}  # Format: {"email": {"status": "success/fail", "last_sent": "timestamp"}}
        self.last_run = last_run  # Last run timestamp for the entire task
    
    def to_dict(self):
        """Convert task to dictionary for storage"""
        return {
            "id": self.task_id,
            "name": self.name,
            "rss_feeds": self.rss_feeds,
            "schedule": self.schedule,
            "recipients": self.recipients,
            "ai_settings": self.ai_settings,
            "feeds_status": self.feeds_status,
            "recipients_status": self.recipients_status,
            "last_run": self.last_run
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
            ai_settings=data.get("ai_settings", {"summary_length": "medium"}),
            feeds_status=data.get("feeds_status", {}),
            recipients_status=data.get("recipients_status", {}),
            last_run=data.get("last_run")
        )
    
    def update_feed_status(self, feed_url, status="success"):
        """Update the status of a feed"""
        self.feeds_status[feed_url] = {
            "status": status,
            "last_fetch": datetime.now().isoformat()
        }
    
    def update_recipient_status(self, email, status="success"):
        """Update the status of an email recipient"""
        self.recipients_status[email] = {
            "status": status,
            "last_sent": datetime.now().isoformat()
        }
    
    def update_task_run(self):
        """Update the last run timestamp for the task"""
        self.last_run = datetime.now().isoformat()
