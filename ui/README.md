# 🖥️ Streamlit UI

The frontend of the BigQuery & Graph AI Assistant, built with Streamlit for a premium, interactive experience.

## ✨ Features

-   **Natural Language Chat**: Interact with BigQuery data as if you're talking to a human analyst.
-   **Instant Visualizations**: High-quality SVG graphs are rendered directly in the chat.
-   **Premium Design**: Custom CSS for a dark-themed, modern look with smooth animations and shadows.
-   **Robust Rendering**: Uses data URIs for SVG display to ensure maximum compatibility across browsers.

## 🔗 Connection to ADK API

The UI communicates with the ADK API server via the following endpoints:

-   `POST /run`: Sends the user prompt and session IDs to the agent. Receives a stream of events (text, tool calls, content).
-   `GET /artifacts/...`: Fetches generated files (like `graph.svg`) for display.

## 🔐 Session Management

Session management in the UI is fully automated and transparent to the user:

1.  **ID Generation**: When the app starts, it checks `st.session_state` for `user_id` and `session_id`. If they don't exist, it generates random 10-character alphanumeric strings.
2.  **Payload Injection**: These IDs are included in every request sent to the `/run` endpoint.
3.  **Chat History**: The UI maintains a local `st.session_state.messages` list to display the conversation history.
4.  **Artifact Fetching**: When the agent generates a graph, the UI uses the `user_id` and `session_id` to construct the correct URL to fetch the artifact from the API server.

## 🛠️ Key Components (`app.py`)

-   `display_image()`: A robust helper that handles SVG extraction, base64 decoding, and data URI rendering.
-   `render_message_parts()`: Processes the complex list of parts returned by the ADK API, ensuring that artifacts are prioritized over raw code.
-   `safe_b64decode()`: Handles various base64 encoding quirks, including URL-safe characters and padding.
