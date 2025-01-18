from typing import Annotated, List

from src.mojentic.channel import Channel
from src.mojentic.event import Event


class EventBroker:
    channels: Annotated[List[Channel], "The channels the event broker manages."]

    def __init__(self):
        self.channels = []

    def add_channel(self, channel: Channel):
        self.channels.append(channel)

    def remove_channel(self, channel: Channel):
        self.channels.remove(channel)

    def send(self, channel_name: str, event: Event):
        for channel in self.channels:
            if channel.name == channel_name:
                channel.enqueue(event)
        self._distribute_events()

    def _distribute_events(self):
        for channel in self.channels:
            if channel.queue:
                event = channel.dequeue()
                for subscriber in channel.subscribers:
                    subscriber.receive_event(event)
