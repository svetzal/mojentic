import logging

from mojentic.agents.iterative_problem_solver import IterativeProblemSolver

logging.basicConfig(level=logging.WARN)

from mojentic.llm.tools.date_resolver import ResolveDateTool
from mojentic.llm.tools.ask_user_tool import AskUserTool
from mojentic.llm import LLMBroker


def main():
    # llm = LLMBroker(model="MFDoom/deepseek-r1-tool-calling:14b")
    # llm = LLMBroker(model="qwen2.5:14b")
    # llm = LLMBroker(model="qwen2.5:14b")
    # llm = LLMBroker(model="qwen2.5:7b")
    llm = LLMBroker(model="qwq")
    # llm = LLMBroker(model="qwq:32b-fp16")
    # llm = LLMBroker(model="llama3.3-70b-32k")

#     user_request = """
# I want to launch a new brand of eco-friendly home cleaning products. Can you create a marketing plan detailing target demographics, promotional channels, a rough budget breakdown, and a timeline of major milestones? Please include example social media copy, key talking points for a press release, and measurable success criteria for each channel. For any photos or graphics, create a prompt I can use with stable-diffusion to generate visuals.
#     """.strip()

    user_request = "What's the date next Friday?"

    ooda = IterativeProblemSolver(
        llm=llm,
        user_request=user_request,
        available_tools=[AskUserTool(), ResolveDateTool()],
        max_iterations=5
    )
    result = ooda.run()
    print(f"User Request:\n{user_request}\n")
    print(f"Agent Response:\n{result}\n")


if __name__ == "__main__":
    main()

audience = """
Our target audience consists of environmentally conscious young women (ages 22-30) who are navigating the challenges of independent living for the first time. These individuals are typically recent graduates or early-career professionals who are balancing entry-level salaries with the high costs of urban living.

Financial Profile:
- Monthly income: $2,500-4,000
- Rent typically consumes 40-50% of their income
- Price-sensitive and budget-conscious
- Actively seeking ways to save money without compromising their values

Environmental Values:
- Deeply committed to reducing their environmental impact
- Willing to pay slightly more for eco-friendly products
- Actively researches product sustainability
- Participates in recycling and waste reduction
- Values transparency in environmental claims

Lifestyle Characteristics:
- Lives in urban areas, often in shared housing or small apartments
- Makes most purchasing decisions independently
- Tech-savvy and social media-active
- Influences peer group purchasing decisions
- Seeks community with shared environmental values

Pain Points:
- Struggles to balance environmental values with budget constraints
- Feels guilty when choosing cheaper, less sustainable options
- Wants to maintain a clean, eco-friendly home without breaking the bank
- Limited storage space for cleaning supplies
- Time-constrained due to work and social commitments

Purchase Behavior:
- Researches products thoroughly before buying
- Relies on peer recommendations and reviews
- Prefers multi-purpose products to save money and space
- Shopping primarily occurs online and at local eco-friendly stores
- Makes careful, considered purchases rather than impulse buys
"""
