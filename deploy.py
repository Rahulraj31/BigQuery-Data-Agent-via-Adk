import vertexai
from data_agent_viz.agent import root_agent
from vertexai.agent_engines import AdkApp
from vertexai import agent_engines
PROJECT_ID =  "rahul-research-test"
LOCATION = "us-central1"
STAGING_BUCKET ="gs://bqagent-mcp-adk-stage"

vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

print(f"Deploying  Agent... on {PROJECT_ID} in {LOCATION} in Bucket {STAGING_BUCKET}")

# Instantiate the class locally (it's safe because set_up hasn't run yet)
adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
)

print("✅ Agent wrapped in AdkApp!")
print("   This app is ready for deployment to Agent Engine.")
try:
    remote_app = agent_engines.create(
        adk_app,
        
            display_name="BQ Viz Data Agent",
            description="BQ Agent",
            requirements=["google-cloud-aiplatform[adk,agent_engines]"],
            extra_packages=["./data_agent_viz"],
        #    service_account="bq-agent-adk@rahul-research-test.iam.gserviceaccount.com" # uncomment this line while deploying
    )

    print("✅ AdkApp deployed successfully!")
    print(f"\nResource name: {remote_app.resource_name}")

except Exception as e:
    print(f"❌ Deployment failed: {e}")
    raise
     