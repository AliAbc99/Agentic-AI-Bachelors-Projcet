'''
This file handles the main application logic for the Stock Advisor Agentic AI.
It is the frontend for the team leader agent, which coordinates multiple agents
it initializes the Streamlit app, sets up the team leader agent, 
manages chat sessions, and provides utilities for user interaction.
'''
import nest_asyncio
import streamlit as st
import traceback

from Team_leader import get_team_leader  # ← team leader agent import
from agno.team.team import Team
from agno.utils.log import logger
from utils import (
    CUSTOM_CSS,
    about_widget,
    add_message,
    display_tool_calls,
    export_chat_history,
    rename_session_widget,
    get_selected,
    load_chat_session,
)

nest_asyncio.apply()
st.set_page_config(
    page_title="Stock Advisor Agentic AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def restart_agent():
    logger.info("---*--- Restarting agent ---*---")
    st.session_state["team_agent"] = None
    st.session_state["team_agent_session_id"] = None
    st.session_state["messages"] = []
    st.rerun()


def main():
    logger.info("main started")
    ####################################################################
    # Header
    ####################################################################
    st.markdown("<h1 class='main-title'>Stock Advisor Agentic AI</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Manages Agents for Smart Reasoning</p>",
        unsafe_allow_html=True,
    )

    ####################################################################
    # Model selector
    ####################################################################
    model_options = {
        "llama 4 - 17B-16E": "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama 3.3 - 70B" : "llama-3.3-70b-versatile",
        "llama 3.1 - 8B": "llama-3.1-8b-instant",        
        "llama 4 - 17B-128E": "meta-llama/llama-4-maverick-17b-128e-instruct",        
    }
    selected_model = st.sidebar.selectbox(
        "Select a model",
        options=list(model_options.keys()),
        index=0,
        key="model_selector",
    )
    model_id = model_options[selected_model]
    ####################################################################
    # Initialize Flags
    ####################################################################
    if ("can_select_flag" not in st.session_state):
        st.session_state["can_select_flag"] = True
        #print(f"can_select_flag created: {st.session_state['can_select_flag']}")

    if ("is_renamed_flag" not in st.session_state):
        st.session_state["is_renamed_flag"] = False
        #print(f"is_renamed_flag created: {st.session_state['is_renamed_flag']}")

    if "create_new_chat" not in st.session_state:
        st.session_state["create_new_chat"] = False
        #print(f"create_new_chat created: {st.session_state['create_new_chat']}")

    ####################################################################
    # Initialize Agent
    ####################################################################
    agent: Team
    if (
        "team_agent" not in st.session_state
        or st.session_state["team_agent"] is None
        or st.session_state.get("current_model") != model_id
    ):
        logger.info("---*--- Creating new Team Agent ---*---")
        agent = get_team_leader(model_id=model_id)
        st.session_state["team_agent"] = agent
        st.session_state["current_model"] = model_id
        logger.info("new agent created")

        #new 
        if st.session_state["create_new_chat"] :
            agent.load_session()
            st.session_state["create_new_chat"] = False
        #new
        st.session_state["team_agent_session_id"] =  agent.session_id #agent.load_session() 
        #print(f"Session created: {st.session_state['team_agent_session_id']}")
        
        #new
        st.session_state["can_select_flag"] = False
        #print("can_select_flag set to False")
        
        
    else:
        agent = st.session_state["team_agent"]
        logger.info("agent loaded from session state")
        st.session_state["can_select_flag"] = True
        #print(f"can_select_flag set to {st.session_state["can_select_flag"]}")
        
        #I should load chat history from agent storage
      #  print(f"before upper session selector with model_id: {model_id}")
      #  session_selector_widget(team=agent ,model_id=st.session_state["current_model"])
       # print("after upper session selector")
        
    
    ####################################################################
    # Load session from memory
    ####################################################################
    session_id_exists = (
        "team_agent_session_id" in st.session_state
        and st.session_state["team_agent_session_id"]
    )

    if not session_id_exists:
        #print("Not exist Session ID")
        try:
            st.session_state["team_agent_session_id"] =  agent.session_id #agent.load_session() #
            #print(f"Session created: {st.session_state['team_agent_session_id']}")

        except Exception as e:
            logger.error(f"Session load error: {str(e)}\n{traceback.format_exc()}")
            st.warning("Could not create session, check backend.")
    elif (
        st.session_state["team_agent_session_id"]
        and hasattr(agent, "memory")
        and agent.memory is not None
        and not agent.memory.runs
    ):
        #print("inside elif")
        try:
            agent.load_session(st.session_state["team_agent_session_id"])
            #print(f"Session loaded: {st.session_state['team_agent_session_id']}")
        except Exception as e:
            logger.error(f"Failed to load session: {str(e)}\n{traceback.format_exc()}")
    

    agent_runs = []
    if hasattr(agent, "memory") and agent.memory is not None:
        agent_runs = agent.memory.runs

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    if len(st.session_state["messages"]) == 0 and len(agent_runs) > 0:
        #print("inside memory run manager")
        for _run in agent_runs:
            if hasattr(_run, "message") and _run.message is not None:
                add_message(_run.message.role, _run.message.content)
            if hasattr(_run, "response") and _run.response is not None:
                add_message("assistant", _run.response.content, _run.response.tools)

    elif len(agent_runs) == 0 and len(st.session_state["messages"]) == 0:
        logger.debug("No previous runs found")

    if prompt := st.chat_input("🧠 Ask me here"):
        add_message("user", prompt)

    ####################################################################
    # Utilities
    ####################################################################
    st.sidebar.markdown("#### 🛠️ Utilities")
    col1, col2 = st.sidebar.columns([1, 1])
    with col1:
        if st.sidebar.button("🔄 New Chat", use_container_width=True):
            st.session_state["create_new_chat"] = True
            restart_agent()
    with col2:
        if st.sidebar.download_button(
            "💾 Export Chat",
            export_chat_history(),
            file_name="team_agent_chat.md",
            mime="text/markdown",
            use_container_width=True,
        ):
            st.sidebar.success("Chat history exported!")

    ####################################################################
    # Delete chat session button
    ####################################################################    
        # 🔸 Delete Button & Confirmation Logic
    if st.sidebar.button("🗑️ Delete Current Chat", use_container_width=True):
        st.session_state["want_delete"] = True

    if st.session_state.get("want_delete"):
        st.sidebar.warning("Are you sure you want to delete this chat?")
        col3, col4 = st.sidebar.columns(2)
        with col3:
            if st.button("✅ Yes", key="confirm_delete_yes"):
                agent.delete_session(st.session_state["team_agent_session_id"])                
                st.session_state["want_delete"] = False
                restart_agent()  # Restart agent to clear state
        with col4:
            if st.button("❌ Cancel", key="confirm_delete_no"):
                st.session_state["want_delete"] = False
                st.rerun()  # Rerun to reset state

    ####################################################################
    # Display chat
    ####################################################################
    
    for message in st.session_state["messages"]:
        if message["role"] in ["user", "assistant"]:
            _content = message["content"]
            if _content:
                with st.chat_message(message["role"]):
                    if "tool_calls" in message and message["tool_calls"]:
                        display_tool_calls(st.empty(), message["tool_calls"])
                    st.markdown(_content)
    
    ####################################################################
    # Respond to user
    ####################################################################
    last_message = (
        st.session_state["messages"][-1] if st.session_state["messages"] else None
    )
    if last_message and last_message.get("role") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            tool_calls_container = st.empty()
            resp_container = st.empty()
            with st.spinner("🤔 Thinking..."):
                response = ""
                try:
                    run_response = agent.run(question, stream=True)
                    for _resp_chunk in run_response:
                        if _resp_chunk.tools and len(_resp_chunk.tools) > 0:
                            display_tool_calls(tool_calls_container, _resp_chunk.tools)
                        if _resp_chunk.content:
                            response += _resp_chunk.content
                            resp_container.markdown(response)
                    add_message("assistant", response, agent.run_response.tools)
                except Exception as e:
                    error_message = f"Sorry, I encountered an error: {str(e)}"
                    add_message("assistant", error_message)                    
                    logger.error(f"Error during agent run: {str(e)}\n{traceback.format_exc()}")
                    st.error(error_message)
        #print("Response sent to chat")
        st.session_state["can_select_flag"] = False
        #print(f"can_select_flag set to {st.session_state['can_select_flag']}")

    ####################################################################
    # Session handling
    ####################################################################
    #print("before session selector")
    #print(f"agent Sid: {agent.session_id}")
    #session_selector_widget(agent, model_id)
    #print(f"is_renamed_flag : {st.session_state['is_renamed_flag']}, can_select_flag: {st.session_state['can_select_flag']}")
    if st.session_state["can_select_flag"] and (st.session_state["is_renamed_flag"] is False): #can select session and not renamed
        selected_S_id = get_selected(agent, default_selected_S_id=st.session_state["team_agent_session_id"])
        if selected_S_id:
            #print(f"Selected session ID: {selected_S_id}")
            if selected_S_id != st.session_state["team_agent_session_id"]:
                st.session_state["team_agent_session_id"] = selected_S_id
                load_chat_session(agent, model_id, selected_S_id)
                st.rerun()
            else:
                #st.session_state["team_agent_session_id"] = selected_S_id
                load_chat_session(agent, model_id, selected_S_id,same_session_id=True) #load selected session_id and write to screen 
        else: #no saved session in agent
            #print("No session saved chat.")
            load_chat_session(agent,  model_id, st.session_state["team_agent_session_id"],) #load selected session_id and write to screen      
    else: #can not select session or is renamed
        selected_S_id = get_selected(team= agent, default_selected_S_id=st.session_state["team_agent_session_id"])         
        #print(f"can not select. loading session: {st.session_state['team_agent_session_id']}")
        st.session_state["is_renamed_flag"] = False
        if st.session_state["is_renamed_flag"] is True: #session name is renamed
            load_chat_session(agent, model_id, st.session_state["team_agent_session_id"])
        else: #same session name
            load_chat_session(agent, model_id, st.session_state["team_agent_session_id"],same_session_id=True) #load selected session_id and write to screen 
        
    #print("after session selector")
    rename_session_widget(agent)

    ####################################################################
    # About section
    ####################################################################
    about_widget()


main()
