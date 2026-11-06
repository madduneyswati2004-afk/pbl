
from datetime import datetime


class Event:
    def __init__(self, event_id, name, date, venue, max_participants):
        self.event_id = event_id
        self.name = name
        self.date = date
        self.venue = venue
        self.max_participants = int(max_participants)

    def display(self, participant_count=0):
        print("-" * 45)
        print(f"Event ID          : {self.event_id}")
        print(f"Event Name        : {self.name}")
        print(f"Date              : {self.date}")
        print(f"Venue             : {self.venue}")
        print(f"Maximum Participants: {self.max_participants}")
        print(f"Registered        : {participant_count}")
        print(f"Available Seats   : {self.max_participants - participant_count}")

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "name": self.name,
            "date": self.date,
            "venue": self.venue,
            "max_participants": self.max_participants
        }

    @staticmethod
    def validate_date(date):
        datetime.strptime(date, "%Y-%m-%d")
        return date
