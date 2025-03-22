from datetime import datetime

class Task:
    """Represents an RSS aggregation task with its own feeds, schedule, and recipients"""
    
    def __init__(self, task_id=None, name="", rss_feeds=None, schedule=None, recipients=None, ai_settings=None,
                 feeds_status=None, recipients_status=None, last_run=None, feed_config=None):
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
        
        # Feed-specific configuration
        self.feed_config = feed_config or {}  # Format: {"feed_url": {"items_count": 10}}
    
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
            "last_run": self.last_run,
            "feed_config": self.feed_config
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a Task instance from dictionary data"""
        # Add debug logging to help troubleshoot
        task_id = data.get("id")
        
        # Create the task instance
        task = cls(
            task_id=task_id,
            name=data.get("name", ""),
            rss_feeds=data.get("rss_feeds", []),
            schedule=data.get("schedule", {"type": "daily", "time": "08:00"}),
            recipients=data.get("recipients", []),
            ai_settings=data.get("ai_settings", {"summary_length": "medium"}),
            feeds_status=data.get("feeds_status", {}),
            recipients_status=data.get("recipients_status", {}),
            last_run=data.get("last_run"),
            feed_config=data.get("feed_config", {})
        )
        
        return task
    
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
    
    def get_feed_items_count(self, feed_url):
        """Get the number of items to fetch for a feed, default is 10"""
        if feed_url in self.feed_config and "items_count" in self.feed_config[feed_url]:
            return self.feed_config[feed_url]["items_count"]
        return 10
    
    def set_feed_items_count(self, feed_url, count):
        """Set the number of items to fetch for a feed"""
        if feed_url not in self.feed_config:
            self.feed_config[feed_url] = {}
        self.feed_config[feed_url]["items_count"] = count
    
    def get_feed_labels(self, feed_url):
        """Get interest labels for a feed, default is empty list"""
        if feed_url in self.feed_config and "labels" in self.feed_config[feed_url]:
            return self.feed_config[feed_url]["labels"]
        return []
    
    def set_feed_labels(self, feed_url, labels):
        """Set interest labels for a feed"""
        if feed_url not in self.feed_config:
            self.feed_config[feed_url] = {}
        self.feed_config[feed_url]["labels"] = labels
