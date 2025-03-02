class EventStore:
    def __init__(self):
        self.events = []

    def store(self, event):
        self.events.append(event)
