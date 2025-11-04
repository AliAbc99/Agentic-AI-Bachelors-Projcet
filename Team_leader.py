from typing import Optional

from agno.agent import Agent
from agno.models.groq import Groq
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from agno.tools.reasoning import ReasoningTools
from agno.storage.sqlite import SqliteStorage
from agno.tools.openbb import OpenBBTools
from uuid import uuid4
from agno.tools.calculator import CalculatorTools

agent_model_id = "llama-3.3-70b-versatile"
#the following modles are also available:
#llama-3.1-8b-instant
#llama-3.3-70b-versatile
team_model_id = "llama-3.3-70b-versatile"
#meta-llama/llama-4-scout-17b-16e-instruct

#agent models could be set seperatly here, otherwise they will default to the agent_model_id
finance_agent_model_id = "llama-3.3-70b-versatile"
web_agent_model_id = "llama-3.3-70b-versatile"


# Groq API key
Groq_api_key = "your_groq_api_key_here"  # replace with your Groq API key :D


'''
Calculator Agent:
- Performs mathematical calculations.
instructions have been tested in different scenarios and are designed to be clear and concise.
intructions are designed based on the Agno GitHub repository and the Agno documentation.
'''
calculator_agent = Agent(
    name="Calculator Agent",
    role="Perform mathematical calculations",
    model=Groq(id=agent_model_id, api_key=Groq_api_key),
    description="You are a calculator agent. Perform calculations based on user requests.", 
    instructions=[
        "You are a calculator agent. Perform calculations based on user requests.",
        "Use the tools provided to perform calculations.",
        "Only output the final answer, no other text.",
    ],
    tools=[
        CalculatorTools(
            add=True,
            subtract=True,
            multiply=True,
            divide=True,
            exponentiate=True,
            factorial=True,
            is_prime=True,
            square_root=True,
            cache_results=True,            
        ),
    ],
    show_tool_calls=True,
    markdown=True,
)


'''
Web Agent:
- Handles web search requests.
- Uses DuckDuckGo for web searches.
- Searches for information on the web.
instructions are designed to be clear and concise.
instructions are designed based on the Agno GitHub repository and the Agno documentation.
'''
web_agent = Agent(
    name="Web Search Agent",
    role="Handle web search requests",
    model=Groq(id=web_agent_model_id if web_agent_model_id else agent_model_id , api_key=Groq_api_key),
    tools=[DuckDuckGoTools(cache_results=True)],
    description = "You are a web search agent. Find information on the web.",
    instructions=[
                "Always include sources",
                "Search 'tradingview + Stock symbol + chart' to find the link to the chart of company",
                "Only output the final answer, no other text.",
                 ],
    add_datetime_to_instructions=True,
    show_tool_calls=True,
)

'''
Finance Agent:
- Handles financial data requests.
- Uses YFinance and OpenBB for financial data.
- Provides stock prices, analyst recommendations, target prices, technical indicators and company information.
instructions are designed to be clear and concise.
instructions are designed based on the Agno GitHub repository and the Agno documentation to be the best fit.
'''
finance_agent = Agent(
    name="Finance Agent",
    role="Handle financial data requests",
    model=Groq(id=finance_agent_model_id if finance_agent_model_id else agent_model_id, api_key=Groq_api_key),
    tools=[
        YFinanceTools(stock_price=True, 
                      analyst_recommendations=True,
                      company_info=False,
                      technical_indicators=True,
                      company_news = True,
                      key_financial_ratios=False,
                      historical_prices=True,
                      cache_results=True,
                      stock_fundamentals=True,                     
                      ),
        OpenBBTools(price_targets = True,
                    search_symbols=True,
                    cache_results=True
                    ),
    ],
    description= "You are a stock market specialist. Provide concise and accurate data.",
    instructions=[
        "Use 'search_company_symbol()' function to find the correct company symbol",        
        "Use the 'get_price_targets' function to get target prices.",
        "Use tables to display stock prices, fundamentals (P/E, Market Cap), and recommendations.",
        "Clearly state the company name and ticker symbol.",
        "Use tools when appropriate. Only call a tool when you are certain of the arguments.",
        "Only use `get_current_stock_price()` for stock prices; do not use price values from `company_info`.",
        "Only output the final answer, no other text."
    ],
    add_datetime_to_instructions=True,
    show_tool_calls=True,
    debug_mode=True,
)

db_table_name="agent_sessions"
Storage_db_file="data.db"
# Create a storage backend using the Sqlite database
team_storage = SqliteStorage(
    # store sessions in the ai.sessions table
    table_name=db_table_name,
    # db_file: Sqlite database file
    db_file=Storage_db_file,
    auto_upgrade_schema=True,
    mode="team", #setting the mode to "team" allows the team leader to store and retrieve team sessions
                #this is critical for the team leader to function properly, since the default mode is "agent"
)

#to ensure the model IDs are set correctly
print (f"Web Agent Model ID: {web_agent.model.id}\nFinance Agent Model ID: {finance_agent.model.id}\nCalculator Agent Model ID: {calculator_agent.model.id}")




def get_team_leader(
                    model_id: Optional[str] = team_model_id,
                    session_name: Optional[str] = None,
                    session_id: Optional[str] = None,
                    debug_mode: bool = False,
                    ) -> Team:
    """Create a team leader agent for stock advisory tasks.
    Args:       
        model_id (str): The model ID for the team leader agent.
        session_name (str): Optional name for the session.
        session_id (str): Optional unique identifier for the session.
        debug_mode (bool): Whether to enable debug mode for the team leader.
    Returns:
        Team: An instance of the Team class representing the team leader agent.
    """

    session_id = session_id or str(uuid4())
    session_name = session_name or "new_session"

    team_leader = Team(
        name="Stock Advisor Team Leader",
        mode="coordinate",    
        model=Groq(id=model_id),
        storage=team_storage,
        team_id="my_team_id",  # Unique identifier for the team
        session_id=session_id,  # Unique identifier for the session
        user_id="my_user_id",  # Unique identifier for the user
        session_name= session_name,  # Name of the session
        members=[
            web_agent,
            finance_agent,
            calculator_agent,
        ],
        tools=[ReasoningTools(add_instructions=True)],
        instructions=[
            "Only output the final answer, no other text.",
            "Answer questions about yourself without using tools.",
            "Use tables to display data",
            "Use Finance Agent for ALL Target Prices.",
            "Use Web Search Agent to find links to charts.",
            "Use Calculator Agent for calculations if needed.",
        ],
        markdown=True,
        show_members_responses=True,
        enable_agentic_context=True, #The Team Leader maintains a shared context that is updated agentically (i.e. by the team leader) and is sent to team members if needed.
        add_datetime_to_instructions=True,
        num_history_runs = 2,
        enable_team_history=True,
        debug_mode=debug_mode,
        success_criteria="The team has successfully completed the task.",
    )

    return team_leader

