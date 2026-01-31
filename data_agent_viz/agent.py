from google.adk.agents.llm_agent import Agent
from .tools import *
from .instructions import graph_agent_instructions, root_agent_instructions

# Graph Sub-Agent
graph_agent = Agent(
    name="GraphAgent",
    model="gemini-2.5-flash",
    tools=[save_graph_artifact],
    description="Specialized in creating graph images and data visualizations using Gemini 2.5 Flash.",
    instruction= graph_agent_instructions
)

# BigQuery Root Agent
root_agent = Agent(
    name="BigQueryAgent",
    model="gemini-2.5-flash",
    tools=[bigquery_toolset],
    sub_agents=[graph_agent],
    instruction=root_agent_instructions
)
