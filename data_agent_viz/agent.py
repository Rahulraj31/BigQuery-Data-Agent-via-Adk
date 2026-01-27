from google.adk.agents.llm_agent import Agent
from .tools import get_bq_toolset, save_graph_artifact
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
bq_toolset = get_bq_toolset()
root_agent = Agent(
    name="BigQueryAgent",
    model="gemini-2.5-flash",
    tools=[bq_toolset],
    sub_agents=[graph_agent],
    instruction=root_agent_instructions
)
