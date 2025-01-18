import threading
from time import sleep
from typing import Annotated, List

from mojentic.channel import Channel
from mojentic.event import Event


class EventBroker:
    channels: Annotated[List[Channel], "The channels the event broker manages."]

    def __init__(self):
        self.channels = []
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._distribute_events)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()

    def add_channel(self, channel: Channel):
        self.channels.append(channel)

    def remove_channel(self, channel: Channel):
        self.channels.remove(channel)

    def send(self, channel_name: str, event: Event):
        for channel in self.channels:
            if channel.name == channel_name:
                channel.enqueue(event)

    def _distribute_events(self):
        while not self._stop_event.is_set():
            for channel in self.channels:
                if channel.queue:
                    event = channel.dequeue()
                    for subscriber in channel.subscribers:
                        subscriber.receive_event(event)
            sleep(1)
