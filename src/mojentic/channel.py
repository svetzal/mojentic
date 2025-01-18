from typing import Annotated, List
from collections import deque

from mojentic.event import Event


class Channel():
    def __init__(self, name: str):
        self.name: str = name
        self.queue: Annotated[deque[Event], "The queue of messages on the channel."] = deque()
        self.subscribers: Annotated[List, "The agents subscribed to the channel."] = []

    def enqueue(self, message):
        self.queue.append(message)

    def dequeue(self):
        return self.queue.popleft()

    def subscribe(self, agent):
        self.subscribers.append(agent)

    def unsubscribe(self, agent):
        self.subscribers.remove(agent)
