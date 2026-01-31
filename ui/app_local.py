import streamlit as st
import os
import requests
import base64
from dotenv import load_dotenv
import random
import string
import re

load_dotenv()

# API Server Configuration
API_URL = "http://127.0.0.1:8000"

def safe_b64decode(data):
    """Robustly decode base64 data, handling padding, URL-safe characters, and raw SVG."""
    if not data:
        return b""
    if not isinstance(data, str):
        return data
        
    clean_data = "".join(data.split())
    
    # If it's already raw SVG, return it
    if "<svg" in clean_data.lower()[:1000]:
        return clean_data.encode("utf-8")
        
    try:
        clean_data = clean_data.replace('-', '+').replace('_', '/')
        missing_padding = len(clean_data) % 4
        if missing_padding:
            clean_data += "=" * (4 - missing_padding)
        return base64.b64decode(clean_data)
    except Exception:
        return data.encode("utf-8")

def display_image(data, mime_type, caption=None):
    """Helper to display images robustly in Streamlit using data URIs."""
    if not data:
        return
    try:
        # Handle SVG
        if mime_type == "image/svg+xml" or (isinstance(data, str) and "<svg" in data.lower()):
            svg_code = data
            if isinstance(data, str) and not "<svg" in data.lower():
                # It's likely base64
                svg_code = safe_b64decode(data).decode("utf-8", errors="ignore")
            
            # Extract only the <svg> block
            svg_match = re.search(r'<svg.*?</svg>', svg_code, re.DOTALL | re.IGNORECASE)
            if svg_match:
                svg_code = svg_match.group(0)
                b64_svg = base64.b64encode(svg_code.encode("utf-8")).decode("utf-8")
                st.markdown(
                    f'<div class="stImage"><img src="data:image/svg+xml;base64,{b64_svg}" style="width:100%"/></div>', 
                    unsafe_allow_html=True
                )
                if caption: st.caption(caption)
                return

        # Handle other formats
        decoded_data = safe_b64decode(data)
        if decoded_data:
            st.image(decoded_data, caption=caption)
            
    except Exception as e:
        st.error(f"Error in display_image: {str(e)}")

def render_message_parts(parts):
    """Renders message parts with nested dictionary support."""
    if not parts:
        return
        
    for part in parts:
        if isinstance(part, str):
            st.markdown(part)
            continue

        # 1. Handle Text
        if "text" in part and part["text"]:
            st.markdown(part["text"])
        
        # 2. Handle direct inline_data
        inline = part.get("inline_data") or part.get("inlineData")
        if inline:
            display_image(inline.get("data"), inline.get("mime_type") or inline.get("mimeType"))
            
        # 3. Handle functionResponse (Crucial for tool outputs)
        func_resp = part.get("functionResponse") or part.get("function_response")
        if func_resp:
            resp_obj = func_resp.get("response")
            if resp_obj:
                # Look for nested inlineData in tool results
                # Tools often return: {"result": {"inlineData": {...}}}
                result = resp_obj.get("result")
                inner_inline = None
                if isinstance(result, dict):
                    inner_inline = result.get("inlineData") or result.get("inline_data")
                
                # If not in result, look at top level of response
                if not inner_inline:
                    inner_inline = resp_obj.get("inlineData") or resp_obj.get("inline_data")
                
                if inner_inline:
                    display_image(inner_inline.get("data"), inner_inline.get("mimeType") or inner_inline.get("mime_type"))

st.set_page_config(page_title="BigQuery & Graph Agent", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    .stImage {
        margin-top: 10px;
        margin-bottom: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        border-radius: 10px;
        background-color: white;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 BigQuery & Graph AI Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
if "session_id" not in st.session_state:
    st.session_state.session_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        render_message_parts(message["content"])

if prompt := st.chat_input("Ask me about your data..."):
    st.session_state.messages.append({"role": "user", "content": [{"text": prompt}]})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Ensure session exists (ADK requirement)
                try:
                    requests.post(f"{API_URL}/apps/data_agent_viz/users/{st.session_state.user_id}/sessions", 
                                  json={"session_id": st.session_state.session_id})
                except: pass

                payload = {
                    "app_name": "data_agent_viz",
                    "user_id": st.session_state.user_id,
                    "session_id": st.session_state.session_id,
                    "new_message": {"role": "user", "parts": [{"text": prompt}]}
                }
                
                response = requests.post(f"{API_URL}/run", json=payload)
                response.raise_for_status()
                events = response.json()
                
                all_parts = []
                for event in events:
                    # Content parts
                    content = event.get("content")
                    if content and "parts" in content:
                        all_parts.extend(content["parts"])
                    
                    # Tool parts
                    actions = event.get("actions", {})
                    func_resps = actions.get("function_responses") or actions.get("functionResponses") or []
                    for resp in func_resps:
                        # Wrap the function response in a structure render_message_parts understands
                        all_parts.append({"function_response": resp})

                    # Artifacts (Fallback if not in tool response)
                    artifact_delta = actions.get("artifact_delta") or actions.get("artifactDelta")
                    if artifact_delta and "graph.svg" in artifact_delta:
                        artifact_url = f"{API_URL}/apps/data_agent_viz/users/{st.session_state.user_id}/sessions/{st.session_state.session_id}/artifacts/graph.svg"
                        try:
                            art_resp = requests.get(artifact_url)
                            if art_resp.status_code == 200:
                                all_parts.append(art_resp.json())
                        except: pass
                
                if all_parts:
                    render_message_parts(all_parts)
                    st.session_state.messages.append({"role": "assistant", "content": all_parts})
                else:
                    st.warning("No response received.")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")