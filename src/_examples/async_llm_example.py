"""
Example script demonstrating how to use the AsyncDispatcher with BaseAsyncLLMAgent.

This script shows how to create and use asynchronous LLM agents with the AsyncDispatcher.
"""

import asyncio
from typing import List, Optional

from pydantic import BaseModel, Field

from mojentic.agents.async_aggregator_agent import AsyncAggregatorAgent
from mojentic.agents.async_llm_agent import BaseAsyncLLMAgent
from mojentic.async_dispatcher import AsyncDispatcher
from mojentic.context.shared_working_memory import SharedWorkingMemory
from mojentic.event import Event
from mojentic.llm import LLMBroker
from mojentic.router import Router


# Define some example events
class QuestionEvent(Event):
    question: str = Field(..., description="The question to answer")


class FactCheckEvent(Event):
    question: str = Field(..., description="The original question")
    facts: List[str] = Field(..., description="The facts related to the question")


class AnswerEvent(Event):
    question: str = Field(..., description="The original question")
    answer: str = Field(..., description="The answer to the question")
    confidence: float = Field(..., description="The confidence level of the answer (0-1)")


class FinalAnswerEvent(Event):
    question: str = Field(..., description="The original question")
    answer: str = Field(..., description="The final answer to the question")
    facts: List[str] = Field(..., description="The facts used to answer the question")
    confidence: float = Field(..., description="The confidence level of the answer (0-1)")


# Define response models for LLM agents
class FactCheckResponse(BaseModel):
    facts: List[str] = Field(..., description="The facts related to the question")


class AnswerResponse(BaseModel):
    answer: str = Field(..., description="The answer to the question")
    confidence: float = Field(..., description="The confidence level of the answer (0-1)")


# Define some example agents
class FactCheckerAgent(BaseAsyncLLMAgent):
    """
    An agent that checks facts related to a question.
    """
    def __init__(self, llm: LLMBroker):
        super().__init__(
            llm=llm,
            behaviour="You are a fact-checking assistant. Your job is to provide relevant facts about a question.",
            response_model=FactCheckResponse
        )

    async def receive_event_async(self, event: Event) -> List[Event]:
        if isinstance(event, QuestionEvent):
            prompt = f"Please provide relevant facts about the following question: {event.question}"
            response = await self.generate_response(prompt)
            return [FactCheckEvent(
                source=type(self),
                correlation_id=event.correlation_id,
                question=event.question,
                facts=response.facts
            )]
        return []


class AnswerGeneratorAgent(BaseAsyncLLMAgent):
    """
    An agent that generates an answer to a question.
    """
    def __init__(self, llm: LLMBroker):
        super().__init__(
            llm=llm,
            behaviour="You are a question-answering assistant. Your job is to provide accurate answers to questions.",
            response_model=AnswerResponse
        )

    async def receive_event_async(self, event: Event) -> List[Event]:
        if isinstance(event, QuestionEvent):
            prompt = f"Please answer the following question: {event.question}"
            response = await self.generate_response(prompt)
            return [AnswerEvent(
                source=type(self),
                correlation_id=event.correlation_id,
                question=event.question,
                answer=response.answer,
                confidence=response.confidence
            )]
        return []


class FinalAnswerAgent(AsyncAggregatorAgent):
    """
    An agent that combines facts and answers to produce a final answer.
    """
    def __init__(self, llm: LLMBroker):
        super().__init__(event_types_needed=[FactCheckEvent, AnswerEvent])
        self.llm = llm
        self.final_answer_event = None

    async def receive_event_async(self, event: Event) -> list:
        print(f"FinalAnswerAgent received event: {type(event).__name__}")
        result = await super().receive_event_async(event)
        # Store any FinalAnswerEvent created
        for e in result:
            if isinstance(e, FinalAnswerEvent):
                self.final_answer_event = e
        return result

    async def process_events(self, events):
        print(f"FinalAnswerAgent processing events: {[type(e).__name__ for e in events]}")
        # Extract the events
        fact_check_event = next((e for e in events if isinstance(e, FactCheckEvent)), None)
        answer_event = next((e for e in events if isinstance(e, AnswerEvent)), None)

        if fact_check_event and answer_event:
            print("FinalAnswerAgent has both FactCheckEvent and AnswerEvent")
            # In a real implementation, we might use the LLM to refine the answer based on the facts
            # For this example, we'll just combine them

            # Adjust confidence based on facts
            confidence = answer_event.confidence
            if len(fact_check_event.facts) > 0:
                # Increase confidence if we have facts
                confidence = min(1.0, confidence + 0.1)

            final_answer_event = FinalAnswerEvent(
                source=type(self),
                correlation_id=fact_check_event.correlation_id,
                question=fact_check_event.question,
                answer=answer_event.answer,
                facts=fact_check_event.facts,
                confidence=confidence
            )
            print(f"FinalAnswerAgent created FinalAnswerEvent: {final_answer_event}")
            self.final_answer_event = final_answer_event
            return [final_answer_event]
        print("FinalAnswerAgent missing either FactCheckEvent or AnswerEvent")
        return []

    async def get_final_answer(self, correlation_id, timeout=30):
        """
        Get the final answer for a specific correlation_id.

        Parameters
        ----------
        correlation_id : str
            The correlation_id to get the final answer for
        timeout : float, optional
            The timeout in seconds

        Returns
        -------
        FinalAnswerEvent or None
            The final answer event, or None if not found
        """
        # First wait for all needed events
        await self.wait_for_events(correlation_id, timeout)

        # Then check if we have a final answer
        if self.final_answer_event and self.final_answer_event.correlation_id == correlation_id:
            return self.final_answer_event

        return None


async def main():
    """
    Main function that demonstrates the usage of AsyncDispatcher with async LLM agents.
    """
    # Initialize the LLM broker with your preferred model
    llm = LLMBroker(model="qwen3:30b-a3b-q4_K_M")

    # Create a router and register agents
    router = Router()

    # Create agents
    fact_checker = FactCheckerAgent(llm)
    answer_generator = AnswerGeneratorAgent(llm)
    final_answer_agent = FinalAnswerAgent(llm)

    # Register agents with the router
    router.add_route(QuestionEvent, fact_checker)
    router.add_route(QuestionEvent, answer_generator)
    router.add_route(QuestionEvent, final_answer_agent)
    router.add_route(FactCheckEvent, final_answer_agent)
    router.add_route(AnswerEvent, final_answer_agent)

    # Create and start the dispatcher
    dispatcher = await AsyncDispatcher(router).start()

    # Create a question event
    question = "What is the capital of France?"
    event = QuestionEvent(source=type("ExampleSource", (), {}), question=question)

    # Dispatch the event
    print("Dispatching question event")
    dispatcher.dispatch(event)

    # Give the dispatcher a moment to start processing the event
    print("Waiting for dispatcher to start processing")
    await asyncio.sleep(0.1)

    # Wait for the final answer from the FinalAnswerAgent
    print("Waiting for final answer from FinalAnswerAgent")
    final_answer_event = await final_answer_agent.get_final_answer(event.correlation_id, timeout=30)

    # Print the final answer
    if final_answer_event:
        print(f"Question: {final_answer_event.question}")
        print(f"Answer: {final_answer_event.answer}")
        print(f"Confidence: {final_answer_event.confidence}")
        print("Facts:")
        for fact in final_answer_event.facts:
            print(f"  - {fact}")
    else:
        print("No FinalAnswerEvent found")

    # Stop the dispatcher
    await dispatcher.stop()


if __name__ == "__main__":
    asyncio.run(main())
