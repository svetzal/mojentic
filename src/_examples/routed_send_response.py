from typing import List

from mojentic.base_agent import BaseAgent
from mojentic.event import Event
from mojentic.router import Router

from mojentic.logger import logger


class ContentEvent(Event):
    content: str


class ContentClassifiedEvent(Event):
    classification: str

class SolicitationClassifiedEvent(ContentClassifiedEvent):
    pass

class GreetingClassifiedEvent(ContentClassifiedEvent):
    pass

class ClassificationCompleteEvent(Event):
    classifications: List[str]



class GreetingClassifierAgent(BaseAgent):
    def receive_event(self, event) -> [Event]:
        output = []
        if "hello" in event.content.lower():
            output.append(GreetingClassifiedEvent(source=type(self), correlation_id=event.correlation_id,
                                                 classification="greeting"))
        else:
            output.append(
                GreetingClassifiedEvent(source=type(self), correlation_id=event.correlation_id, classification="other"))
        return output

class SolicitationClassifierAgent(BaseAgent):
    def receive_event(self, event) -> [Event]:
        output = []
        if "buy" in event.content.lower():
            output.append(SolicitationClassifiedEvent(source=type(self), correlation_id=event.correlation_id,
                                                 classification="solicitation"))
        else:
            output.append(
                SolicitationClassifiedEvent(source=type(self), correlation_id=event.correlation_id, classification="other"))
        return output


class CorrelationAggregatorAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.aggregated = {}
        self.results = {}
        self.needed = []

    def _get_and_reset_results(self, event):
        results = self.results[event.correlation_id]
        self.aggregated[event.correlation_id] = []
        self.results[event.correlation_id] = []
        return results

    def _capture_results_if_needed(self, event):
        if event.source in self.needed:
            results = self.results.get(event.correlation_id, [])
            results.append(event)
            self.results[event.correlation_id] = results

    def _register_correlation_id(self, event):
        seen = self.aggregated.get(event.correlation_id, [])
        seen.append(event.source)
        self.aggregated[event.correlation_id] = seen
        return seen

    def _has_all_needed(self, seen):
        finished = all([agent in seen for agent in self.needed])
        logger.debug(f"Seen: {seen}, Needed: {self.needed}, Finished: {finished}")
        return finished


class ClassificationAggregatorAgent(CorrelationAggregatorAgent):
    def __init__(self):
        super().__init__()
        self.needed = [SolicitationClassifierAgent, GreetingClassifierAgent]

    def receive_event(self, event) -> [Event]:
        seen = self._register_correlation_id(event)
        self._capture_results_if_needed(event)

        if self._has_all_needed(seen):
            filtered_results = [r.classification for r in self._get_and_reset_results(event) if r.classification != "other"]
            return [ClassificationCompleteEvent(source=type(self), correlation_id=event.correlation_id,
                                                classifications=filtered_results)]
        return []


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
    GreetingClassifiedEvent: [aggregate_agent],
    SolicitationClassifiedEvent: [aggregate_agent],
    ClassificationCompleteEvent: [output_agent]
}, batch_size=10)

router.dispatch(ContentEvent(source=str, content="Hello, World"))
router.dispatch(ContentEvent(source=str, content="Buy now!"))
