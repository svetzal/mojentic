"""
Example script demonstrating how to use the AsyncDispatcher, BaseAsyncAgent, and AsyncAggregatorAgent.

This script shows how to create and use asynchronous agents with the AsyncDispatcher.
"""

import asyncio
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from mojentic.agents.async_aggregator_agent import AsyncAggregatorAgent
from mojentic.agents.async_llm_agent import BaseAsyncLLMAgent
from mojentic.agents.base_async_agent import BaseAsyncAgent
from mojentic.async_dispatcher import AsyncDispatcher
from mojentic.event import Event, TerminateEvent
from mojentic.llm import LLMBroker
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.router import Router


# Define some example events
class TextEvent(Event):
    text: str = Field(..., description="The text content of the event")


class AnalysisEvent(Event):
    analysis: str = Field(..., description="The analysis of the text")


class SummaryEvent(Event):
    summary: str = Field(..., description="The summary of the text")


class CombinedResultEvent(Event):
    text: str = Field(..., description="The original text")
    analysis: str = Field(..., description="The analysis of the text")
    summary: str = Field(..., description="The summary of the text")
    combined: str = Field(..., description="The combined result")


# Define response models for LLM agents
class AnalysisResponse(BaseModel):
    analysis: str = Field(..., description="The analysis of the text")


class SummaryResponse(BaseModel):
    summary: str = Field(..., description="The summary of the text")


class CombinedResponse(BaseModel):
    combined: str = Field(..., description="The combined result of the analysis and summary")


# Define some example agents
class TextAnalyzerAgent(BaseAsyncLLMAgent):
    """
    An agent that analyzes text and produces an analysis.
    """

    def __init__(self, llm: LLMBroker):
        super().__init__(
            llm=llm,
            behaviour="You are a text analysis assistant. Your job is to provide a detailed analysis of the given text, including key themes, structure, and notable elements.",
            response_model=AnalysisResponse
        )

    async def receive_event_async(self, event: Event) -> List[Event]:
        if isinstance(event, TextEvent):
            prompt = f"""
Please analyze the following text in detail. Consider:
- Main themes and topics
- Structure and organization
- Key points and arguments
- Style and tone
- Intended audience
- Any notable or unique elements

Text to analyze:
{event.text[:1000]}... (text truncated for brevity)
"""
            response = await self.generate_response(prompt)
            return [AnalysisEvent(source=type(self), correlation_id=event.correlation_id, analysis=response.analysis)]
        return []


class TextSummarizerAgent(BaseAsyncLLMAgent):
    """
    An agent that summarizes text.
    """

    def __init__(self, llm: LLMBroker):
        super().__init__(
            llm=llm,
            behaviour="You are a text summarization assistant. Your job is to provide concise, accurate summaries of texts while preserving the key information and main points.",
            response_model=SummaryResponse
        )

    async def receive_event_async(self, event: Event) -> List[Event]:
        if isinstance(event, TextEvent):
            prompt = f"""
Please provide a concise summary of the following text. The summary should:
- Capture the main points and key information
- Be significantly shorter than the original text
- Maintain the original meaning and intent
- Be clear and coherent
- Exclude unnecessary details

Text to summarize:
{event.text[:1000]}... (text truncated for brevity)
"""
            response = await self.generate_response(prompt)
            return [SummaryEvent(source=type(self), correlation_id=event.correlation_id, summary=response.summary)]
        return []


class ResultCombinerAgent(AsyncAggregatorAgent):
    """
    An agent that combines the analysis and summary of a text using LLM.
    """

    def __init__(self, llm: LLMBroker):
        super().__init__(event_types_needed=[TextEvent, AnalysisEvent, SummaryEvent])
        self.llm = llm
        self.behaviour = "You are an assistant that combines text analysis and summaries into a comprehensive report."
        self.response_model = CombinedResponse

    async def process_events(self, events):
        # Extract the events
        text_event = next((e for e in events if isinstance(e, TextEvent)), None)
        analysis_event = next((e for e in events if isinstance(e, AnalysisEvent)), None)
        summary_event = next((e for e in events if isinstance(e, SummaryEvent)), None)

        if text_event and analysis_event and summary_event:
            # Use LLM to create a sophisticated combination
            prompt = f"""
I have analyzed and summarized a text. Please combine these into a comprehensive report.

Original Text (excerpt): {text_event.text[:300]}... (text truncated for brevity)

Analysis: {analysis_event.analysis}

Summary: {summary_event.summary}

Please create a well-structured, insightful report that integrates the analysis and summary, 
highlighting the most important aspects of the text. The report should provide a comprehensive 
understanding of the text's content, structure, and significance.
"""
            # Create a temporary LLM agent to generate the response
            messages = [
                LLMMessage(role=MessageRole.System, content=self.behaviour),
                LLMMessage(role=MessageRole.User, content=prompt)
            ]

            # Generate the response
            import asyncio
            response_json = await asyncio.to_thread(
                self.llm.generate_object,
                messages=messages,
                object_model=self.response_model
            )

            combined = response_json.combined

            return [CombinedResultEvent(
                source=type(self),
                correlation_id=text_event.correlation_id,
                text=text_event.text,
                analysis=analysis_event.analysis,
                summary=summary_event.summary,
                combined=combined
            )]
        return []


class ResultOutputAgent(BaseAsyncAgent):
    """
    An agent that receives the CombinedResultEvent, outputs the result to the user,
    and emits a TerminateEvent to exit the event loop.
    """

    async def receive_event_async(self, event: Event) -> List[Event]:
        if isinstance(event, CombinedResultEvent):
            # Output the result to the user
            print("\n=== FINAL ANSWER ===")
            print(event.combined)
            print("===================\n")

            # Emit a TerminateEvent to exit the event loop
            return [TerminateEvent(source=type(self), correlation_id=event.correlation_id)]
        return []


async def main():
    """
    Main function that demonstrates the usage of AsyncDispatcher and async agents.
    """
    # Initialize the LLM broker with the same model as in async_llm_example
    llm = LLMBroker(model="qwen3:30b-a3b-q4_K_M")

    # Create a router and register agents
    router = Router()

    # Create agents with LLM
    analyzer = TextAnalyzerAgent(llm)
    summarizer = TextSummarizerAgent(llm)
    combiner = ResultCombinerAgent(llm)
    output_agent = ResultOutputAgent()

    # Register agents with the router
    router.add_route(TextEvent, analyzer)
    router.add_route(TextEvent, summarizer)
    router.add_route(TextEvent, combiner)
    router.add_route(AnalysisEvent, combiner)
    router.add_route(SummaryEvent, combiner)
    router.add_route(CombinedResultEvent, output_agent)

    # Create and start the dispatcher
    dispatcher = await AsyncDispatcher(router).start()

    # Create a text event
    with open(Path.cwd().parent.parent / "README.md", "r") as f:
        text = f.read()
    event = TextEvent(source=type("ExampleSource", (), {}), text=text)

    # Dispatch the event
    dispatcher.dispatch(event)

    # Wait for all events in the queue to be processed
    print("Waiting for all events to be processed...")
    queue_empty = await dispatcher.wait_for_empty_queue(timeout=10)
    if not queue_empty:
        print("Warning: Not all events were processed within the timeout period.")

    # Stop the dispatcher
    await dispatcher.stop()


if __name__ == "__main__":
    asyncio.run(main())
