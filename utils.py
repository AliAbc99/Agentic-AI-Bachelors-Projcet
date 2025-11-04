from typing import Any, Dict, List, Optional

import streamlit as st
from Team_leader import get_team_leader
from agno.team.team import Team
from agno.utils.log import logger
import traceback

#appends messages to the session messages. Not showing them.
def add_message( 
    role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None
) -> None:
    if "messages" not in st.session_state or not isinstance(st.session_state["messages"], list):
        st.session_state["messages"] = []
    st.session_state["messages"].append(
        {"role": role, "content": content, "tool_calls": tool_calls}
    )


def export_chat_history():
    if "messages" in st.session_state:
        chat_text = "# Stock Advisor Team - Chat History\n\n"
        for msg in st.session_state["messages"]:
            role = "🤖 Assistant" if msg["role"] == "agent" else "👤 User"
            chat_text += f"### {role}\n{msg['content']}\n\n"
            if msg.get("tool_calls"):
                chat_text += "#### Tools Used:\n"
                for tool in msg["tool_calls"]:
                    tool_name = tool.get("name", "Unknown Tool") if isinstance(tool, dict) else getattr(tool, "name", "Unknown Tool")
                    chat_text += f"- {tool_name}\n"
        return chat_text
    return ""


def display_tool_calls(tool_calls_container, tools):
    if not tools:
        return

    with tool_calls_container.container():
        for tool_call in tools:
            if isinstance(tool_call, dict):
                _tool_name = tool_call.get("tool_name") or tool_call.get("name") or "Unknown Tool"
                _tool_args = tool_call.get("tool_args") or tool_call.get("arguments") or {}
                _content = tool_call.get("content") or tool_call.get("result", "")
                _metrics = tool_call.get("metrics", {})
            else:
                _tool_name = getattr(tool_call, "tool_name", None) or getattr(tool_call, "name", None) or "Unknown Tool"
                _tool_args = getattr(tool_call, "tool_args", None) or getattr(tool_call, "arguments", None) or {}
                _content = getattr(tool_call, "content", None) or getattr(tool_call, "result", "")
                _metrics = getattr(tool_call, "metrics", {})

            if hasattr(tool_call, "function"):
                if hasattr(tool_call.function, "name"):
                    _tool_name = tool_call.function.name
                if hasattr(tool_call.function, "arguments"):
                    _tool_args = tool_call.function.arguments

            title = f"🛠️ {_tool_name.replace('_', ' ').title() if _tool_name else 'Tool Call'}"
            with st.expander(title, expanded=False):
                if isinstance(_tool_args, dict) and "query" in _tool_args:
                    st.code(_tool_args["query"], language="sql")
                elif isinstance(_tool_args, str):
                    try:
                        import json
                        st.markdown("**Arguments:**")
                        st.json(json.loads(_tool_args))
                    except:
                        st.markdown("**Arguments:**")
                        st.markdown(f"```\n{_tool_args}\n```")
                elif _tool_args and _tool_args != {"query": None}:
                    st.markdown("**Arguments:**")
                    st.json(_tool_args)

                if _content:
                    st.markdown("**Results:**")
                    try:
                        st.json(_content) if isinstance(_content, (dict, list)) else st.markdown(_content)
                    except:
                        st.markdown(_content)

                if _metrics:
                    st.markdown("**Metrics:**")
                    st.json(_metrics)


def rename_session_widget(team: Team) -> None:
    container = st.sidebar.container()
    if "session_edit_mode" not in st.session_state:
        st.session_state.session_edit_mode = False

    if st.sidebar.button("✎ Rename Session"):
        st.session_state.session_edit_mode = True
        st.rerun()

    if st.session_state.session_edit_mode:
        new_session_name = st.sidebar.text_input("Enter new name:", value=team.session_name, key="session_name_input")
        if st.sidebar.button("Save", type="primary"):
            if new_session_name:
                try:
                    team.rename_session(new_session_name)
                    #team.session_name = new_session_name
                    st.session_state.session_edit_mode = False
                    st.session_state["is_renamed_flag"] = True
                    #print(f"is_renamed_flag set to {st.session_state['is_renamed_flag']}")
                    st.session_state["can_select_flag"] = False
                    #print(f"can_select_flag set to {st.session_state['can_select_flag']}")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Error renaming session: {str(e)}\n{traceback.format_exc()}")
                    st.sidebar.error(f"Error renaming session: {str(e)}")

def load_chat_session(team: Team, model_id: str, selected_session_id: str, same_session_id : Optional[bool] = False) -> None:
    if team.storage: #all teams have a storage
        team_sessions = team.storage.get_all_sessions()

        session_options = []
        for session in team_sessions:
            session_id = session.session_id
            session_name = session.session_data.get("session_name", None) if session.session_data else None
            display_name = session_name if session_name else session_id
            session_options.append({"id": session_id, "display": display_name})

        #print(f"session_options: {session_options}")

        if session_options:
            #selected_session = st.sidebar.selectbox("Session", options=[s["display"] for s in session_options], key="session_selector")
            #selected_session_id = next(s["id"] for s in session_options if s["display"] == selected_session)
            #selected_session_id= selected_id

            #print(f"existing session_id: {st.session_state.get('team_agent_session_id')} and selected session_id: {selected_session_id}")
            #if st.session_state.get("team_agent_session_id") != selected_session_id :
            #print("not same existing session_id and selected")
            logger.info(f"---*--- Loading {model_id} run: {selected_session_id} ---*---")
            try:
                if not same_session_id:
                    new_team = get_team_leader(session_id=selected_session_id, model_id=model_id)
                    st.session_state["team_agent"] = new_team
                    #("not same session name, new team created")
                
                
                st.session_state["team_agent_session_id"] = selected_session_id
                st.session_state["messages"] = []

                selected_session_obj = next((s for s in team_sessions if s.session_id == selected_session_id), None)
                if selected_session_obj and selected_session_obj.memory and "runs" in selected_session_obj.memory:
                    #print("in selector if, runs found")
                    seen_messages = set()
                    for run in selected_session_obj.memory["runs"]:
                        if "messages" in run:
                            for msg in run["messages"]:
                                role, content = msg.get("role"), msg.get("content")
                                if not content or role == "system":
                                    continue
                                msg_id = f"{role}:{content}"
                                if msg_id not in seen_messages:
                                    seen_messages.add(msg_id)
                                    if role == "assistant":
                                        tool_calls = msg.get("tool_calls") or run.get("tools")
                                        add_message(role, content, tool_calls)
                                    else:
                                        add_message(role, content)
                        elif "message" in run and isinstance(run["message"], dict):
                            user_msg = run["message"]["content"]
                            if f"user:{user_msg}" not in seen_messages:
                                seen_messages.add(f"user:{user_msg}")
                                add_message("user", user_msg)

                            if "content" in run and run["content"]:
                                asst_msg = run["content"]
                                if f"assistant:{asst_msg}" not in seen_messages:
                                    seen_messages.add(f"assistant:{asst_msg}")
                                    add_message("assistant", asst_msg, run.get("tools"))
                #st.rerun()
              #  for message in st.session_state["messages"]: #show messages in the chat
              #      if message["role"] in ["user", "assistant"]:
              #          _content = message["content"]
               #         if _content:
                #            with st.chat_message(message["role"]):
               #                 if "tool_calls" in message and message["tool_calls"]:
               #                     display_tool_calls(st.empty(), message["tool_calls"])
                #                st.markdown(_content)

            except Exception as e:
                logger.error(f"Error switching sessions: {str(e)} \n{traceback.format_exc()}")
                st.sidebar.error(f"Error loading session: {str(e)}")
            #else:
               # print(f"Session already loaded: {selected_session_id}")
        else:
            st.sidebar.info("No saved sessions available.")


def get_selected(team: Team, default_selected_S_id : Optional[str] = None) -> str:
    if team.storage: #all teams have a storage
        team_sessions = team.storage.get_all_sessions()

        session_options = []
        for session in team_sessions:
            session_id = session.session_id
            session_name = session.session_data.get("session_name", None) if session.session_data else None
            #print(f"session_name: {session_name} and session_id: {session_id}")
            display_name = session_name if session_name else "New Chat"  # Default display name if session_name is None
            session_options.append({"id": session_id, "display": display_name})

        #print(f"session_options: {session_options}")

        if session_options:
            # Compute index of the default session ID if provided
            default_index = next(
                (i for i, s in enumerate(session_options) if s["id"] == default_selected_S_id),
                0  # fallback to first if not found
            )
            selected_session = st.sidebar.selectbox(
                                                    "Session",
                                                    options=session_options,               # full dicts
                                                    index=default_index,
                                                    format_func=lambda s: s["display"],    # what the user sees
                                                    key="session_selector"
                                                )
            #print(f"selected session: {selected_session}")
            selected_session_id = selected_session["id"]       # no ambiguity            
            #print(f"selected session_id: {selected_session_id}")
            return selected_session_id
        else:
            st.sidebar.info("No saved sessions available.")
            #print("slected session_id: None")
            return None
        


def about_widget() -> None:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ About")
    st.sidebar.markdown("""
    This Stock Advisor Agent Team answers finance-related questions and could advice you in the US stock market.

    Built By:
    - 🧠 Ali
    - 🖥️ "Engineering Project"
    """)


CUSTOM_CSS = """
    <style>
    /* Main Styles */
    .main-title {
        text-align: center;
        background: linear-gradient(45deg, #28a745, #218838); /* nice green gradient */
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3em;
        font-weight: bold;
        padding: 1em 0;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2em;
    }
    .stButton button {
        width: 100%;
        border-radius: 20px;
        margin: 0.2em 0;
        transition: all 0.3s ease;
        cursor: pointer;
        background: linear-gradient(45deg, #28a745, #218838);
        color: white;
        border: none;
        font-weight: 600;
        box-shadow: 0 3px 6px rgba(33, 136, 56, 0.4);
    }
    .stButton button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(33, 136, 56, 0.6);
    }
    .chat-container {
        border-radius: 15px;
        padding: 1em;
        margin: 1em 0;
        background-color: #f5f5f5;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        transition: background-color 0.3s ease;
    }
    /* Tool result section */
    .tool-result {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 1.2em 1.5em;
        margin: 1.5em 0;
        border-left: 6px solid #218838;
        box-shadow: 0 6px 18px rgba(33, 136, 56, 0.15);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #333;
        transition: box-shadow 0.3s ease;
    }
    .tool-result:hover {
        box-shadow: 0 10px 25px rgba(33, 136, 56, 0.3);
    }
    .tool-result-title {
        font-weight: 700;
        margin-bottom: 0.5em;
        font-size: 1.25em;
        color: #28a745;
    }
    .status-message {
        padding: 1em;
        border-radius: 10px;
        margin: 1em 0;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
    }
    /* Dark mode adjustments */
    @media (prefers-color-scheme: dark) {
        .chat-container {
            background-color: #2b2b2b;
            box-shadow: 0 4px 12px rgba(33, 136, 56, 0.15);
            color: #ddd;
        }
        .tool-result {
            background-color: #1e1e1e;
            border-left-color: #218838;
            box-shadow: 0 6px 18px rgba(33, 136, 56, 0.4);
            color: #eee;
        }
        .tool-result:hover {
            box-shadow: 0 10px 25px rgba(33, 136, 56, 0.6);
        }
        .tool-result-title {
            color: #4caf50;
        }
        .success-message {
            background-color: #1e4620;
            color: #c7f0c4;
        }
        .error-message {
            background-color: #4a1c20;
            color: #f7b2b8;
        }
    }
    </style>
"""

