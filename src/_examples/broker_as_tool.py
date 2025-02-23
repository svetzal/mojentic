import os
from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.date_resolver import ResolveDateTool
from mojentic.llm.tools.file_manager import FileManager, ListFilesTool, ReadFileTool, WriteFileTool
from mojentic.llm.tools.tool_wrapper import ToolWrapper

#
# This is largely a fail, but it was interesting.
#

temporal_specialist = BaseLLMAgent(
    llm=LLMBroker(model="qwen2.5:7b"),
    tools=[ResolveDateTool()],
    behaviour="You are a historian and sociologist who focuses on sorting out temporal events, determining what happened or will happen when."
)

knowledge_specialist = BaseLLMAgent(
    llm=LLMBroker(model="llama3.3-70b-32k"),
    tools=[
        ListFilesTool(path="local"),
        ReadFileTool(path="local"),
        WriteFileTool(path="local"),
    ],
    behaviour="You are a knowledge management agent who focuses on sorting out facts and information, able to organize elemental ideas and make connections between them. You can list files to find out where you stored information, read files to review that information, and write files to store that information for later retrieval."
)

if not os.path.exists("local"):
    os.mkdir("local")



coordinator = BaseLLMAgent(
    llm=LLMBroker(model="llama3.3-70b-32k"),
    behaviour="You are a coordinator who can manage multiple agents and delegate tasks to them to solve problems.",
    tools=[
        ToolWrapper(temporal_specialist, "temporal_specialist", "A historian and sociologist who focuses on sorting out temporal events, figuring out dates, determining what happened or will happen when."),
        ToolWrapper(knowledge_specialist, "knowledge_specialist", "A knowledge management specialist who focuses on sorting out facts and information, able to organize elemental ideas and make connections between them. Can list files to find out where you stored information, read files to review that information, and write files to store that information for later retrieval."),
    ]
)

result = coordinator.generate_response("""

I have several things I need to do this week:
                                       
- On Monday, I need to ensure that I have called Scotiabank and ordered replacement cards for my current, credit, and line of credit accounts.
- On Wednesday, I need to drive into Toronto for work. While in Toronto I need to pick up razors. I need to make sure I see Gregg, Britney and Vikram.
- On Thursday, I need to ensure I'm up by 7am so that I can be showered and ready for work by 9.
- On Friday, I need to ensure that I have my laundry done and my bags packed for my trip to Ottawa.
                                       
Create me a markdown file for each day of the week, named "YYYY-MM-DD-ToDo.md" where the date is the date of that day.
Make a list of to-do items in the markdown file, and add a section for the day's daily notes that I can fill out each day.
""")

print(result)