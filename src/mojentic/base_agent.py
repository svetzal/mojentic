from mojentic.event import Event


class BaseAgent():

    def receive_event(self, event: Event) -> [Event]:
        return []
