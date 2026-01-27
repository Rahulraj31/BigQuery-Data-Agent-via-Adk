# 🤖 AI Agents & Tools

This folder contains the core intelligence of the application, defined using the ADK (Agent Development Kit).

## 👥 Agents

### 1. BigQueryAgent (`agent.py`)
- **Role**: Data Analyst Expert.
- **Responsibilities**:
    - Discovers tables and schemas in BigQuery.
    - Writes and executes SQL queries.
    - Delegates visualization tasks to the `GraphAgent`.
- **Tools**: Uses the `BigQueryToolset` for direct database interaction.
- **Instructions**: Uses `root_agent_instructions` from `instructions.py`.

### 2. GraphAgent (`agent.py`)
- **Role**: Visualization Specialist.
- **Responsibilities**:
    - Generates high-quality SVG code for data visualizations.
    - Follows strict readability rules (no overlapping text, proper margins).
    - Uses a self-verification loop to ensure professional output.
- **Tools**: Uses `save_graph_artifact` to store visualizations.
- **Instructions**: Uses `graph_agent_instructions` from `instructions.py`.

## 📜 Instructions (`instructions.py`)

This file centralizes the agent personas and operational protocols, making it easy to tune agent behavior without touching the core logic in `agent.py`.

## 🛠️ Tools (`tools.py`)

-   `get_bq_toolset()`: Configures and returns the BigQuery toolset with write permissions.
-   `save_graph_artifact(svg_code)`: An asynchronous tool that:
    1.  Encodes the RAW SVG string.
    2.  Saves it as an ADK artifact named `graph.svg`.
    3.  Returns a `types.Part` object for immediate display.

## 🔐 Session Management

Session management in the agent layer is handled automatically by the ADK framework:

1.  **Context Injection**: Every tool call (like `save_graph_artifact`) receives a `ToolContext`.
2.  **ID Propagation**: The `ToolContext` contains the `user_id` and `session_id` passed from the UI.
3.  **Artifact Storage**: When `save_graph_artifact` is called, it uses these IDs to store the file in the correct user/session directory on the API server.
4.  **Persistence**: The ADK API server uses these IDs to retrieve the correct chat history and artifacts for each user.
