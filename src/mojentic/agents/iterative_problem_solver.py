from typing import List

import structlog

from mojentic.llm import LLMBroker, ChatSession
from mojentic.llm.tools.llm_tool import LLMTool

logger = structlog.get_logger()


class IterativeProblemSolver:
    """An agent that solves problems iteratively using available tools.

    This solver breaks down complex problems into steps, using available tools to accomplish
    the task. It maintains context throughout the process and provides structured results.

    Attributes:
        user_request: The original request to be processed
        max_loops: Maximum number of iterations before giving up
        chat: The chat session maintaining conversation context

    The final result is formatted according to whether the task succeeded or failed:
    - For successful tasks:
        - Direct answer or solution
        - Relevant outputs and results
        - Concise, solution-focused response
    - For failed tasks:
        - Specific explanation of what couldn't be accomplished
        - Description of partial progress (if any)
        - Suggested alternatives (where applicable)

    The response maintains professionalism and focuses on outcomes rather than process.
    """
    user_request: str
    max_loops: int
    chat: ChatSession

    def __init__(self, llm: LLMBroker, user_request: str, available_tools: List[LLMTool], max_loops: int = 3):
        self.available_tools = available_tools
        self.user_request = user_request
        self.max_loops = max_loops
        self.chat = ChatSession(
            llm=llm,
            system_prompt="""You are an advanced problem-solving agent with the following capabilities and responsibilities:

1. Strategic Thinking:
   - Break down complex problems into manageable steps
   - Plan ahead and anticipate potential challenges
   - Adapt your approach based on intermediate results

2. Tool Expertise:
   - Analyze available tools and their optimal use cases
   - Select the most appropriate tools for each task
   - Combine tools effectively when needed

3. Progress Management:
   - Track progress towards the goal
   - Identify and handle edge cases
   - Maintain context across multiple steps

4. Quality Standards:
   - Ensure accuracy and completeness of solutions
   - Validate results before proceeding
   - Provide clear, actionable outputs

Your role is to solve user requests efficiently while maintaining high standards of reliability and effectiveness.""",
            tools=available_tools,
        )

    def step(self) -> str:
        prompt = f"""
Given the user request:
{self.user_request}

Approach this task systematically:

1. ANALYSIS
   - Review the current state and progress
   - Identify the next key objective
   - List relevant tools for this step

2. EXECUTION
   - Use selected tools to accomplish the objective
   - Validate results before proceeding
   - Document any important outputs

3. STATUS ASSESSMENT
Respond with one of:
   - "DONE: <brief result>" if the task is completed successfully
   - "CONTINUE: <progress summary> | <next step>" if more steps are needed
   - "FAIL: <specific reason> | <attempted approach> | <suggested alternative>" if unsuccessful

Remember to:
- Use tools strategically and combine them when beneficial
- Maintain context across steps
- Adapt your approach based on intermediate results
"""
        return self.chat.send(prompt)

    def run(self):
        loops_remaining = self.max_loops
        progress_history = []

        while True:
            result = self.step()
            print(result)

            # Parse the response
            status = result.split(":")[0].strip().upper()
            details = result[result.find(":")+1:].strip() if ":" in result else ""

            if status == "FAIL":
                stop_message = f"Task failed: {details}"
                break
            elif status == "DONE":
                stop_message = f"Task completed: {details}"
                break
            elif status == "CONTINUE":
                progress_summary, next_step = details.split("|") if "|" in details else (details, "")
                progress_history.append({"summary": progress_summary.strip(), "next": next_step.strip()})

            loops_remaining -= 1
            if loops_remaining == 0:
                stop_message = f"Task failed: max loops reached. Progress made: {len(progress_history)} steps"
                break

        print(stop_message)

        success = status == "DONE"
        progress_summary = "\n".join([f"- {p['summary']}" for p in progress_history]) if progress_history else "No intermediate steps recorded"

        final_prompt = f"""
Given the original user request:
{self.user_request}

Task Status: {"Succeeded" if success else "Failed"}
Progress Summary:
{progress_summary}

Provide a comprehensive final response with the following structure:

1. Solution Status (Required)
   - Outcome: Clear statement of the final result
   - Confidence Level: High/Medium/Low with brief justification
   - Quality Metrics: Completeness, accuracy, and reliability assessment

2. If Successful:
   - Primary Solution: Direct and actionable answer
   - Key Results: Specific outputs or findings
   - Validation: How the solution was verified
   - Limitations: Any constraints or assumptions

3. If Failed:
   - Blocking Issues: Specific obstacles encountered
   - Progress Made: Valuable intermediate results
   - Alternative Approaches: Other potential solutions
   - Next Steps: Recommended actions

Guidelines:
- Prioritize clarity and actionability
- Include quantitative metrics where possible
- Focus on outcomes and value delivered
- Maintain professional and direct tone
"""
        result = self.chat.send(final_prompt)

        return result
