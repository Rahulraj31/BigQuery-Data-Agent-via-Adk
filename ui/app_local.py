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
    """Robustly decode base64 data, handling padding, URL-safe characters, and invalid characters."""
    if not data:
        return b""
    if not isinstance(data, str):
        return data
        
    # Remove whitespace and newlines
    clean_data = "".join(data.split())
    
    # If it's already raw SVG, just return it
    if "<svg" in clean_data.lower()[:1000]:
        return clean_data.encode("utf-8")
        
    try:
        # Handle URL-safe base64
        clean_data = clean_data.replace('-', '+').replace('_', '/')
        # Fix padding
        missing_padding = len(clean_data) % 4
        if missing_padding:
            clean_data += "=" * (4 - missing_padding)
        return base64.b64decode(clean_data)
    except Exception:
        # If it fails, maybe it's raw text
        return data.encode("utf-8")

def is_likely_base64(s):
    """Check if a string is likely base64 encoded image data."""
    if not isinstance(s, str): return False
    clean_s = "".join(s.split())
    if len(clean_s) < 100: return False
    # Check if it only contains base64 characters (including URL-safe ones)
    return bool(re.match(r'^[A-Za-z0-9+/_\-]*={0,2}$', clean_s))

def display_image(data, mime_type, caption=None):
    """Helper to display images robustly in Streamlit using data URIs."""
    if not data:
        return
    try:
        # 1. Handle SVG (either raw string or base64)
        is_svg = (mime_type == "image/svg+xml")
        svg_code = None
        
        if isinstance(data, str):
            if "<svg" in data.lower():
                svg_match = re.search(r'<svg.*?</svg>', data, re.DOTALL | re.IGNORECASE)
                if svg_match:
                    svg_code = svg_match.group(0)
                    is_svg = True
            elif is_likely_base64(data):
                decoded = safe_b64decode(data)
                if b"<svg" in decoded.lower()[:2000]:
                    svg_code = decoded.decode("utf-8", errors="ignore")
                    is_svg = True
        
        if is_svg:
            if not svg_code:
                # Try to decode if we don't have it yet
                try:
                    svg_code = safe_b64decode(data).decode("utf-8", errors="ignore")
                except:
                    pass
            
            if svg_code:
                # Clean up SVG
                start_idx = svg_code.lower().find("<svg")
                if start_idx != -1:
                    svg_code = svg_code[start_idx:]
                
                # Use data URI in an img tag for maximum compatibility and to avoid CSS clashes
                b64_svg = base64.b64encode(svg_code.encode("utf-8")).decode("utf-8")
                st.markdown(
                    f'<div class="stImage"><img src="data:image/svg+xml;base64,{b64_svg}"/></div>', 
                    unsafe_allow_html=True
                )
                if caption:
                    st.caption(caption)
                return

        # 2. Handle other images
        decoded_data = safe_b64decode(data)
        if decoded_data:
            st.image(decoded_data, caption=caption)
            
    except Exception as e:
        st.error(f"Error in display_image: {str(e)}")

def render_message_parts(parts):
    """Renders a list of message parts with deduplication and priority logic."""
    if not parts:
        return
        
    # Identification of components
    has_explicit_image = any(
        ("inline_data" in p or "inlineData" in p) or 
        ("functionResponse" in p or "function_response" in p) or
        ("result" in p and ("inline_data" in p["result"] or "inlineData" in p["result"]))
        for p in parts if isinstance(p, dict)
    )
    
    for part in parts:
        if not isinstance(part, dict):
            continue
            
        # 1. Handle text
        text = part.get("text")
        if text:
            # If we have an explicit image, skip SVG-like content in text to avoid duplication
            if has_explicit_image and ("<svg" in text.lower() or is_likely_base64(text)):
                continue
            
            # If it's a standalone SVG/base64 in text, render it
            if "<svg" in text.lower() or is_likely_base64(text):
                display_image(text, "image/svg+xml")
            else:
                st.markdown(text)
        
        # 2. Handle inline_data
        inline_data = part.get("inline_data") or part.get("inlineData")
        if inline_data:
            mime_type = inline_data.get("mime_type") or inline_data.get("mimeType")
            data = inline_data.get("data")
            display_image(data, mime_type)
            
        # 3. Handle functionResponse (which might contain inlineData)
        func_resp = part.get("functionResponse") or part.get("function_response")
        if func_resp:
            response_obj = func_resp.get("response")
            if isinstance(response_obj, dict):
                # Check for inline_data directly in response (ADK style)
                inner_inline = response_obj.get("inline_data") or response_obj.get("inlineData")
                
                # Check for result with inlineData (ADK/Gemini style)
                if not inner_inline:
                    result = response_obj.get("result")
                    if isinstance(result, dict):
                        inner_inline = result.get("inlineData") or result.get("inline_data")
                
                if inner_inline:
                    mime = inner_inline.get("mimeType") or inner_inline.get("mime_type")
                    data = inner_inline.get("data")
                    display_image(data, mime)

st.set_page_config(page_title="BigQuery & Graph Agent", page_icon="📊", layout="wide")

# Custom CSS for a premium look
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .stImage {
        margin-top: 10px;
        margin-bottom: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        border-radius: 10px;
        background-color: #f8f9fa; /* Light background for visibility */
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 BigQuery & Graph AI Assistant")
st.markdown("Query your data and generate visualizations instantly.")

# Chat history and session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Automated session management
if "user_id" not in st.session_state:
    st.session_state.user_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
if "session_id" not in st.session_state:
    st.session_state.session_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if isinstance(message["content"], str):
            st.markdown(message["content"])
        else:
            render_message_parts(message["content"])

# User input
if prompt := st.chat_input("Ask me about your data or to generate a graph..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Ensure session exists
                try:
                    requests.post(
                        f"{API_URL}/apps/data_agent_viz/users/{st.session_state.user_id}/sessions", 
                        json={"session_id": st.session_state.session_id}
                    )
                except:
                    pass

                # Prepare the request to ADK API Server
                payload = {
                    "app_name": "data_agent_viz",
                    "user_id": st.session_state.user_id,
                    "session_id": st.session_state.session_id,
                    "new_message": {
                        "role": "user",
                        "parts": [{"text": prompt}]
                    }
                }
                
                response = requests.post(f"{API_URL}/run", json=payload)
                response.raise_for_status()
                events = response.json()
                
                # Collect all parts from all events
                all_parts = []
                for event in events:
                    # 1. Parts from content
                    content = event.get("content")
                    if content and "parts" in content:
                        all_parts.extend(content["parts"])
                    
                    # 2. Parts from function responses in actions
                    actions = event.get("actions")
                    if actions:
                        func_resps = actions.get("function_responses") or actions.get("functionResponses")
                        if func_resps:
                            for resp in func_resps:
                                # Append the function response as a part for render_message_parts to handle
                                all_parts.append({"function_response": resp})
                                
                                # Compatibility: also check if 'response' has 'parts'
                                response_content = resp.get("response")
                                if isinstance(response_content, dict) and "parts" in response_content:
                                    all_parts.extend(response_content["parts"])

                        # 3. Artifacts from artifact_delta
                        artifact_delta = actions.get("artifact_delta") or actions.get("artifactDelta")
                        if artifact_delta and "graph.svg" in artifact_delta:
                            artifact_url = f"{API_URL}/apps/data_agent_viz/users/{st.session_state.user_id}/sessions/{st.session_state.session_id}/artifacts/graph.svg"
                            try:
                                art_resp = requests.get(artifact_url)
                                art_resp.raise_for_status()
                                art_data = art_resp.json() # This is a types.Part
                                all_parts.append(art_data)
                            except:
                                pass
                
                if all_parts:
                    render_message_parts(all_parts)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": all_parts
                    })
                else:
                    st.warning("No response content received from the agent.")
                    
            except Exception as e:
                st.error(f"Error connecting to API: {str(e)}")