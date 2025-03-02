from typing import Type

from mojentic.agents.ooda.models import PotentialActions


class TaskGraph:
    def __init__(self, user_request: str):
        self.user_request = user_request
        self.potential_actions = PotentialActions(list=[])

    @property
    def available_tasks(self):
        return len(self.potential_actions.list)

    def add_potential_actions(self, potential_actions: Type[PotentialActions]):
        self.potential_actions.list.extend(potential_actions.list)
