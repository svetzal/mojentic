from mojentic.base_agent import BaseAgent
from mojentic.channel import Channel
from mojentic.event import Event
from mojentic.event_broker import EventBroker


class ContentEvent(Event):
    content: str


class ReceiverAgent(BaseAgent):
    def receive_event(self, event):
        self.event_broker.send("response_channel", ContentEvent(content="Hello, " + event.content))

class OutputAgent(BaseAgent):
    def receive_event(self, event):
        print(event.content)


send_channel = Channel("send_channel")
response_channel = Channel("response_channel")

eb = EventBroker()
eb.add_channel(send_channel)
eb.add_channel(response_channel)

send_channel.subscribe(ReceiverAgent(eb))
response_channel.subscribe(OutputAgent(eb))

eb.send("send_channel", ContentEvent(content="World"))