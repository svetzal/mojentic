from typing import List

from mojentic.base_agent import BaseAgent
from mojentic.correlation_aggregator_agent import CorrelationAggregatorAgent
from mojentic.event import Event
from mojentic.router import Router


#
# Declare domain specific events
#

class ContentEvent(Event):
    content: str


class ContentClassifiedEvent(Event):
    content: str
    classification: str


class SolicitationClassifiedEvent(ContentClassifiedEvent):
    pass


class GreetingClassifiedEvent(ContentClassifiedEvent):
    pass


class ClassificationCompleteEvent(Event):
    content: str
    classifications: List[str]


#
# Declare domain specific agents
#

class GreetingClassifierAgent(BaseAgent):
    def receive_event(self, event) -> [Event]:
        output = []
        if "hello" in event.content.lower():
            output.append(GreetingClassifiedEvent(source=type(self),
                                                  correlation_id=event.correlation_id,
                                                  content=event.content,
                                                  classification="greeting"))
        else:
            output.append(
                GreetingClassifiedEvent(source=type(self),
                                        correlation_id=event.correlation_id,
                                        content=event.content,
                                        classification="other"))
        return output


class SolicitationClassifierAgent(BaseAgent):
    def receive_event(self, event) -> [Event]:
        output = []
        if "buy" in event.content.lower():
            output.append(SolicitationClassifiedEvent(source=type(self),
                                                      correlation_id=event.correlation_id,
                                                      content=event.content,
                                                      classification="solicitation"))
        else:
            output.append(
                SolicitationClassifiedEvent(source=type(self),
                                            correlation_id=event.correlation_id,
                                            content=event.content,
                                            classification="other"))
        return output


class ClassificationAggregatorAgent(CorrelationAggregatorAgent):
    def __init__(self):
        super().__init__([GreetingClassifiedEvent, SolicitationClassifiedEvent])

    def receive_event(self, event) -> [Event]:
        if self._has_all_needed(event):
            filtered_results = [r.classification for r in self._get_and_reset_results(event) if
                                r.classification != "other"]
            return [ClassificationCompleteEvent(source=type(self), correlation_id=event.correlation_id,
                                                content=event.content,
                                                classifications=filtered_results)]
        return []


class OutputAgent(BaseAgent):
    def receive_event(self, event) -> [Event]:
        print(event)
        return []


#
# Set up the system
#

output_agent = OutputAgent()
classifier_agent = GreetingClassifierAgent()
classifier_agent2 = SolicitationClassifierAgent()
aggregate_agent = ClassificationAggregatorAgent()

# This is very explicitly declared, if each Agent declared what event types it can consume, we could make this reactive
router = Router({
    ContentEvent: [classifier_agent, classifier_agent2],
    GreetingClassifiedEvent: [aggregate_agent],
    SolicitationClassifiedEvent: [aggregate_agent],
    ClassificationCompleteEvent: [output_agent]
}, batch_size=10)

#
# Send in events!
#

router.dispatch(ContentEvent(source=str, content="Hello, World"))
router.dispatch(ContentEvent(source=str, content="Buy now!"))
