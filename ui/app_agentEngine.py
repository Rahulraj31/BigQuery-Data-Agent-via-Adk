import streamlit as st
import os
import requests
import base64
from dotenv import load_dotenv
import random
import string
import re
import vertexai
from vertexai import agent_engines

load_dotenv()

# Vertex AI Configuration
PROJECT_ID = os.getenv("PROJECT_ID", "rahul-research-test")
LOCATION = os.getenv("LOCATION", "us-central1")
RESOURCE_NAME = "projects/rahul-research-test/locations/us-central1/agentEngines/bq-viz-data-agent" # Replace with your actual resource name if different

vertexai.init(project=PROJECT_ID, location=LOCATION)

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

def find_inline_data(obj):
    """Recursively search for inline_data/inlineData in a dictionary or object."""
    if obj is None:
        return None
        
    # If it's a Part object (handled by SDK), check its attributes
    if not isinstance(obj, dict):
        inline = getattr(obj, "inline_data", None) or getattr(obj, "inlineData", None)
        if inline: return find_inline_data(inline)
        
        # Check for 'result' attribute
        result = getattr(obj, "result", None)
        if result: return find_inline_data(result)
        
        # Check for 'response' attribute
        response = getattr(obj, "response", None)
        if response: return find_inline_data(response)
        return None
    
    # Check current level (if dict)
    inline = obj.get("inline_data") or obj.get("inlineData")
    if inline and isinstance(inline, dict) and ("data" in inline or "mime_type" in inline or "mimeType" in inline):
        return inline
        
    # Check for 'result' wrapper
    result = obj.get("result")
    if result:
        res = find_inline_data(result)
        if res: return res
        
    # Check for 'response' wrapper
    response = obj.get("response")
    if response:
        res = find_inline_data(response)
        if res: return res
        
    # Check all values recursively
    for v in obj.values():
        res = find_inline_data(v)
        if res: return res
    return None

def render_message_parts(parts):
    """Renders a list of message parts with deduplication and priority logic."""
    if not parts:
        return
        
    # Identification of components
    has_explicit_image = any(
        find_inline_data(p) is not None
        for p in parts
    )
    
    for part in parts:
        # Normalize part keys (SDK might use attributes)
        if isinstance(part, dict):
            text = part.get("text")
        else:
            text = getattr(part, "text", None)

        # 1. Handle text
        if text:
            # If we have an explicit image, skip SVG-like content in text to avoid duplication
            if has_explicit_image and ("<svg" in text.lower() or is_likely_base64(text)):
                continue
            
            # If it's a standalone SVG/base64 in text, render it
            if "<svg" in text.lower() or is_likely_base64(text):
                display_image(text, "image/svg+xml")
            else:
                st.markdown(text)
        
        # 2. Handle inline_data (at any level)
        inline = find_inline_data(part)
        if inline:
            # SDK uses mime_type, dict might use mimeType
            mime_item = inline.get("mimeType") or inline.get("mime_type") if isinstance(inline, dict) else getattr(inline, "mime_type", None)
            data_item = inline.get("data") if isinstance(inline, dict) else getattr(inline, "data", None)
            display_image(data_item, mime_item)

st.set_page_config(page_title="BigQuery Data Agent", page_icon="📊", layout="wide")

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

st.markdown("<h1 style='text-align: center;'>BigQuery Data Agent</h1>", unsafe_allow_html=True)
st.markdown("<h5 style='text-align: center;'>Query your data and generate visualizations instantly.</h5>", unsafe_allow_html=True)

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
                # Load the agent
                agent = agent_engines.get(RESOURCE_NAME)
                
                # Query the agent
                # Note: session_id is used for context persistence
                response = agent.query(
                    input=prompt,
                    session_id=st.session_state.session_id
                )
                
                # Collect all parts from all events
                all_parts = []
                
                # iterate through the response events
                for event in response:
                    # 1. Handle content parts
                    content = getattr(event, "content", None) or (event.get("content") if isinstance(event, dict) else None)
                    if content:
                        parts = getattr(content, "parts", []) if not isinstance(content, dict) else content.get("parts", [])
                        for p in parts:
                            if hasattr(p, "to_dict"):
                                all_parts.append(p.to_dict())
                            elif isinstance(p, dict):
                                all_parts.append(p)
                            else:
                                # Fallback for text parts or custom objects
                                text_val = getattr(p, "text", None) or (p.get("text") if isinstance(p, dict) else str(p))
                                all_parts.append({"text": text_val})
                    
                    # 2. Handle actions (including function responses)
                    actions = getattr(event, "actions", None) or (event.get("actions") if isinstance(event, dict) else None)
                    if actions:
                        # Function responses
                        func_resps = getattr(actions, "function_responses", []) if not isinstance(actions, dict) else (actions.get("function_responses") or actions.get("functionResponses"))
                        if func_resps:
                            for resp in func_resps:
                                # Add the whole response for robust rendering
                                resp_data = resp.to_dict() if hasattr(resp, "to_dict") else resp
                                all_parts.append({"function_response": resp_data})
                                
                                # Also check for nested parts if provided
                                resp_obj = getattr(resp, "response", None) if not isinstance(resp, dict) else resp.get("response")
                                if resp_obj:
                                    inner_parts = getattr(resp_obj, "parts", []) if not isinstance(resp_obj, dict) else resp_obj.get("parts", [])
                                    for ip in inner_parts:
                                        if hasattr(ip, "to_dict"):
                                            all_parts.append(ip.to_dict())
                                        else:
                                            all_parts.append(ip)
                
                if all_parts:
                    render_message_parts(all_parts)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": all_parts
                    })
                else:
                    st.warning("No response content received from the agent.")
                    
            except Exception as e:
                st.error(f"Error connecting to Agent Engine: {str(e)}")
                st.info("Check if your RESOURCE_NAME is correct and you have active credentials.")
