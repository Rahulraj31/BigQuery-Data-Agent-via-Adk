import os
import tempfile
from typing import Any
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode
from google.genai import types
from google.adk.tools.tool_context import ToolContext
  



# Initialize BigQuery Toolset
os.environ["GOOGLE_CLOUD_PROJECT"] = "rahul-research-test"
base_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(base_dir, "service-cred.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_path

def get_bq_toolset():
    tool_config = BigQueryToolConfig(write_mode=WriteMode.ALLOWED)
    return BigQueryToolset(bigquery_tool_config=tool_config) 




async def save_graph_artifact(svg_code: str, tool_context: ToolContext) -> Any:
    """
    Saves the generated SVG code as an artifact and returns it for display.
    Args:
        svg_code: The raw SVG string for the visualization (NOT Python code).
        tool_context: The tool context for saving artifacts.
    Returns:
        A types.Part object containing the SVG image.
    """
    print(f"DEBUG: save_graph_artifact called with {len(svg_code)} chars of SVG")
    # Encode SVG to bytes
    svg_bytes = svg_code.encode('utf-8')
    
    # Create the part
    part = types.Part.from_bytes(
        data=svg_bytes,
        mime_type="image/svg+xml"
    )

    # Save to Artifact Service if available
    # Accessing protected member _invocation_context to get artifact service
    inv_ctx = tool_context._invocation_context
    if inv_ctx.artifact_service:
        await inv_ctx.artifact_service.save_artifact(
            app_name=inv_ctx.app_name,
            user_id=inv_ctx.user_id,
            session_id=inv_ctx.session.id,
            filename="graph.svg",
            artifact=part
        )

    return part