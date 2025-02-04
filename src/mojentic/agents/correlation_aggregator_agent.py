import structlog

from mojentic.agents.base_agent import BaseAgent

logger = structlog.get_logger()


class BaseAggregatingAgent(BaseAgent):
    def __init__(self, event_types_needed=[]):
        super().__init__()
        self.results = {}
        self.event_types_needed = event_types_needed

    def _get_and_reset_results(self, event):
        results = self.results[event.correlation_id]
        self.results[event.correlation_id] = None
        return results

    def _capture_results_if_needed(self, event):
        # if type(event) in self.event_types_needed:
        results = self.results.get(event.correlation_id, [])
        results.append(event)
        self.results[event.correlation_id] = results

    def _has_all_needed(self, event):
        self._capture_results_if_needed(event)
        event_types_captured = [type(e) for e in self.results.get(event.correlation_id, [])]
        finished = all([event_type in event_types_captured for event_type in self.event_types_needed])
        logger.debug(f"Captured: {event_types_captured}, Needed: {self.event_types_needed}, Finished: {finished}")
        return finished
