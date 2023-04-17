from datetime import datetime
import uuid


# Category class
class Category():
    def __init__(self, title, id="", deleted=False):
        self.title = title
        self.id = id      
        self.deleted = deleted

    # Return dictionary representation of object
    def dict(self):
        return {
            "title": self.title,            
            "id": self.id,            
            "deleted": self.deleted
        }
