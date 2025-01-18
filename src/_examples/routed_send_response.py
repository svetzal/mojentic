import logging
from typing import List

from mojentic.base_agent import BaseAgent
from mojentic.event import Event
from mojentic.router import Router

from mojentic.logger import logger

class ContentEvent(Event):
    content: str


class ContentClassifiedEvent(Event):
    classification: str


class ClassificationCompleteEvent(Event):
    classifications: List[str]


class GreetingClassifierAgent(BaseAgent):
    def receive_event(self, event) -> [Event]:
        output = []
        if "hello" in event.content.lower():
            output.append(ContentClassifiedEvent(source=type(self), correlation_id=event.correlation_id,
                                                 classification="greeting"))
        else:
            output.append(
                ContentClassifiedEvent(source=type(self), correlation_id=event.correlation_id, classification="other"))
        return output


class SolicitationClassifierAgent(BaseAgent):
    def receive_event(self, event) -> [Event]:
        output = []
        if "buy" in event.content.lower():
            output.append(ContentClassifiedEvent(source=type(self), correlation_id=event.correlation_id,
                                                 classification="solicitation"))
        else:
            output.append(
                ContentClassifiedEvent(source=type(self), correlation_id=event.correlation_id, classification="other"))
        return output


class ClassificationAggregatorAgent(BaseAgent):
    def __init__(self):
        self.classifications = {}
        self.results = {}
        self.needed = [SolicitationClassifierAgent, GreetingClassifierAgent]

    def receive_event(self, event) -> [Event]:
        seen = self.classifications.get(event.correlation_id, [])
        seen.append(event.source)
        self.classifications[event.correlation_id] = seen

        if event.source in self.needed:
            results = self.results.get(event.correlation_id, [])
            results.append(event.classification)
            self.results[event.correlation_id] = results

        if self._has_all_needed(seen):
            self.classifications[event.correlation_id] = []
            filtered_results = [result for result in self.results[event.correlation_id] if result != "other"]
            return [ClassificationCompleteEvent(source=type(self), correlation_id=event.correlation_id,
                                                classifications=filtered_results)]
        return []

    def _has_all_needed(self, seen):
        finished = all([agent in seen for agent in self.needed])
        logger.debug(f"Seen: {seen}, Needed: {self.needed}, Finished: {finished}")
        return finished


class OutputAgent(BaseAgent):
    def receive_event(self, event) -> [Event]:
        print(event)
        return []


output_agent = OutputAgent()
classifier_agent = GreetingClassifierAgent()
classifier_agent2 = SolicitationClassifierAgent()
aggregate_agent = ClassificationAggregatorAgent()

router = Router({
    ContentEvent: [classifier_agent, classifier_agent2],
    ContentClassifiedEvent: [aggregate_agent],
    ClassificationCompleteEvent: [output_agent]
})

router.dispatch(ContentEvent(source=str, content="Hello, World"))
router.dispatch(ContentEvent(source=str, content="Buy now!"))
