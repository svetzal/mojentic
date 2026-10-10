from mojentic.agents.correlation_aggregator_agent import BaseAggregatingAgent
from mojentic.event import Event


class DescribeAggregatorDefaults:
    def should_isolate_default_event_types_between_agents(self):
        first = BaseAggregatingAgent()
        second = BaseAggregatingAgent()

        first.event_types_needed.append(Event)

        assert second.event_types_needed == []

    def should_preserve_explicit_event_type_list_identity(self):
        needed = [Event]

        agent = BaseAggregatingAgent(needed)

        assert agent.event_types_needed is needed
