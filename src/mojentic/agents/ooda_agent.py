from datetime import datetime
from typing import Optional, List

import structlog

from mojentic.agents.ooda.models import PotentialActions, PotentialAction, Action
from mojentic.agents.ooda.task_graph import TaskGraph
from mojentic.llm import LLMBroker
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.utils.formatting import print_green

logger = structlog.get_logger()


class OodaAgent:
    """
    This is currently not a subclass of BaseAgent, while I figure out what I really want the Agent interface to be.
    I want to have the notion of an agent that can be run individually, and if I want to put it in a system of agents
    I just want to wrap it in an event processor / emitter.
    """
    task_graph: TaskGraph
    current_observations: str
    next_action: Optional[PotentialAction]
    current_action: Optional[Action]
    past_actions: [Action]
    llm: LLMBroker

    def __init__(self, llm: LLMBroker, user_request: str, available_tools: List[LLMTool], max_loops: int = 3):
        self.llm = llm
        self.task_graph = TaskGraph(user_request)
        self.available_tools = available_tools
        self.current_observation = None
        self.next_action = None
        self.current_action = None
        self.past_actions = []
        self.max_loops = max_loops

    def tools_prompt_fragment(self):
        return "\n".join([f"- {tool.name}: {tool.description}" for tool in self.available_tools])

    def observe(self):
        self.next_action = None
        self.current_action = None

        prompt = f"""
Given the user request:
{self.task_graph.user_request}

And what's been done so far:
{self._past_actions_summary()}

And the tools you have available:
{self.tools_prompt_fragment()}

Summarize your observations of the current situation.
        """.strip()

        logger.info("Observe", prompt=prompt)
        print_green(prompt)
        self.current_observation = self.llm.generate(messages=[LLMMessage(content=prompt)])
        return self.current_observation

    def _past_actions_summary(self):
        if self.past_actions:
            items = []
            for action in self.past_actions:
                items.append(
                    f"[{action.started_at.strftime('%Y-%m-%d %H:%M:%S')}] {action.action} - {action.reasoning}")
                if action.result:
                    items.append(f"  - Result: {action.result}")
                if action.tool_calls:
                    items.append("  - Tools:")
                    for tool_call in action.tool_calls:
                        items.append(f"    - {tool_call.content}")
            history = "\n".join(items)
        else:
            history = "No actions have been taken yet."
        return history

    def orient(self):
        prompt = f"""
Given the user request:
{self.task_graph.user_request}

And what's been done so far:
{self._past_actions_summary()}

And your observations of the current situation:
{self.current_observation}

And the tools you have available:
{self.tools_prompt_fragment()}

What are the potential actions that could be taken?
        """.strip()

        logger.info("Orient", prompt=prompt)
        print_green(prompt)
        actions = self.llm.generate_object(messages=[LLMMessage(content=prompt)], object_model=PotentialActions)
        self.task_graph.add_potential_actions(actions)
        return actions

    def decide(self):
        prompt = f"""
Given the user request:
{self.task_graph.user_request}

And what's been done so far:
{self._past_actions_summary()}

And your observations of the current situation:
{self.current_observation}

And the tools you have available:
{self.tools_prompt_fragment()}

And the potential actions:
{self.task_graph.potential_actions.model_dump_json()}

What is the next action to take?
- If you do not believe we can satisfy the user's request, specify an action of "FAIL"
- If you believe you have completed this request, and simply wish to inform the user of your result, specify an action of "DONE".
- If you have not satisfied the user's request, select the next action you want to take.
        """.strip()

        logger.info("Decide", prompt=prompt)
        print_green(prompt)
        result = self.llm.generate_object(messages=[LLMMessage(content=prompt)], object_model=PotentialAction)
        self.next_action = result
        return self.next_action

    def act(self):
        self.current_action = Action(
            action=self.next_action.action,
            reasoning=self.next_action.reasoning,
            context=self.current_observation,
            started_at=datetime.now()
        )
        self.next_action = None

        prompt = f"""
Given the user request:
{self.task_graph.user_request}

And your observations of the current situation:
{self.current_observation}

And the action you've chosen:
{self.current_action.action} - {self.current_action.reasoning}

Perform the action, and report the results.
        """.strip()

        logger.info("Act", prompt=prompt)
        print_green(prompt)
        messages = [LLMMessage(content=prompt)]
        result = self.llm.generate(messages=messages, tools=self.available_tools)
        self.current_action.result = result
        self.current_action.tool_calls = [m for m in messages if m.role == MessageRole.Tool]
        self.past_actions.append(self.current_action)

        self.current_action = None
        return self.past_actions[-1]

    def run(self):
        loops_remaining = self.max_loops
        stop_message = None

        while True:
            result = self.observe()
            print(result)

            result = self.orient()
            print(result)

            result = self.decide()
            print(result)
            if "FAIL".lower() in result.action.lower():
                stop_message = f"Task failed: {result}"
                break
            elif "DONE".lower() in result.action.lower():
                stop_message = f"Task completed: {result}"
                break

            result = self.act()
            print(result)

            loops_remaining -= 1
            if loops_remaining == 0:
                stop_message = "Task failed: max loops reached"
                break

        return stop_message
