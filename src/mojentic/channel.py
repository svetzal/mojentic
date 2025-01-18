from typing import Annotated, List
from collections import deque

from src.mojentic.event import Event


class Channel:
    name: Annotated[str, "The name of the channel."]
    queue: Annotated[deque[Event], "The queue of messages on the channel."] = deque()
    subscribers: Annotated[List, "The agents subscribed to the channel."] = []

    def __init__(self, name: str):
        self.name = name

    def enqueue(self, message):
        self.queue.append(message)

    def dequeue(self):
        return self.queue.popleft()

    def subscribe(self, agent):
        self.subscribers.append(agent)

    def unsubscribe(self, agent):
        self.subscribers.remove(agent)
