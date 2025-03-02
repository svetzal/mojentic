from _pytest.fixtures import fixture

from mojentic.agents.ooda.models import PotentialAction, PotentialActions
from mojentic.agents.ooda.task_graph import TaskGraph


@fixture
def user_request() -> str:
    return "user request"


@fixture
def task_graph(user_request) -> TaskGraph:
    return TaskGraph(user_request)


class DescribeTaskGraph:
    """
    The Task Graph contains the history of tasks run, and the optional future potential tasks that might be chosen.
    """

    def should_start_empty(self, user_request):
        """
        Given we need to create a task graph
        When the task graph is created
        Then the task graph should be empty
        """
        task_graph = TaskGraph(user_request)

        assert task_graph.available_tasks == 0

    def should_register_new_available_options(self, task_graph):
        """
        Given we have some potential actions
        When actions are added to the task graph
        Then we can recall them later
        """
        potential_action = PotentialAction(action="action", reasoning="reasoning")

        task_graph.add_potential_actions(PotentialActions(list=[
            potential_action
        ]))

        assert task_graph.available_tasks == 1
        assert task_graph.potential_actions == PotentialActions(list=[potential_action])
