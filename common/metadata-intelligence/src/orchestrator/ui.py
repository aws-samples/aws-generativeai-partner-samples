"""Streamlit UI for the SQL Agent."""

import streamlit as st
import asyncio
import os
from .agent import SQLAgent
from .models import AgentRequest


def get_connection_string():
    """Get database connection string from environment or user input."""
    # Try environment first
    conn_str = os.getenv('DATABASE_URL')
    
    if not conn_str:
        st.sidebar.header("Database Configuration")
        host = st.sidebar.text_input("Host", value="localhost")
        port = st.sidebar.text_input("Port", value="5432")
        database = st.sidebar.text_input("Database", value="postgres")
        username = st.sidebar.text_input("Username", value="postgres")
        password = st.sidebar.text_input("Password", type="password")
        
        if all([host, port, database, username, password]):
            conn_str = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    return conn_str


async def run_agent_query(agent, user_query):
    """Run agent query asynchronously."""
    request = AgentRequest(user_query=user_query)
    return await agent.process_request(request)


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="SQL Agent",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 SQL Agent")
    st.markdown("Natural language to SQL with planner/executor pattern")
    
    # Get connection string
    conn_str = get_connection_string()
    
    if not conn_str:
        st.error("Please configure database connection in the sidebar or set DATABASE_URL environment variable.")
        return
    
    # Initialize agent
    if 'agent' not in st.session_state:
        st.session_state.agent = SQLAgent(conn_str)
    
    # Main interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Query Interface")
        
        user_query = st.text_area(
            "Enter your query in natural language:",
            placeholder="e.g., Show me all users from the users table",
            height=100
        )
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("Execute Query", type="primary"):
                if user_query:
                    with st.spinner("Processing query..."):
                        try:
                            response = asyncio.run(run_agent_query(st.session_state.agent, user_query))
                            
                            st.subheader("Results")
                            
                            # Show plan
                            if response.plan:
                                st.write("**Generated SQL:**")
                                st.code(response.plan.translated_query, language="sql")
                                st.write(f"**Explanation:** {response.plan.explanation}")
                            
                            # Show results
                            if response.result and response.result.success:
                                if response.result.data:
                                    st.write("**Query Results:**")
                                    st.dataframe(response.result.data)
                                st.success(f"Query executed successfully in {response.result.execution_time_ms:.2f}ms")
                            elif response.result:
                                st.error(f"Query failed: {response.result.error_message}")
                            else:
                                st.error(f"Agent error: {response.message}")
                        
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                else:
                    st.warning("Please enter a query.")
        
        with col_btn2:
            if st.button("Validate Only"):
                if user_query:
                    with st.spinner("Validating query..."):
                        try:
                            response = asyncio.run(run_agent_query(st.session_state.agent, user_query))
                            if response.plan:
                                st.code(response.plan.translated_query, language="sql")
                                if response.plan.validation_passed:
                                    st.success("Query validation passed!")
                                else:
                                    st.error("Query validation failed!")
                                st.write(response.plan.explanation)
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
    
    with col2:
        st.header("Database Schema")
        
        if st.button("Refresh Schema"):
            try:
                with st.spinner("Loading schema..."):
                    tables = asyncio.run(st.session_state.agent.get_schema_info())
                    st.session_state.schema = tables
            except Exception as e:
                st.error(f"Error loading schema: {str(e)}")
        
        if 'schema' in st.session_state:
            for table in st.session_state.schema:
                with st.expander(f"📋 {table.name}"):
                    st.write(f"**Schema:** {table.schema}")
                    if table.columns:
                        st.write("**Columns:**")
                        for col in table.columns:
                            st.write(f"- {col.get('name', 'unknown')} ({col.get('type', 'unknown')})")
                    if table.primary_keys:
                        st.write(f"**Primary Keys:** {', '.join(table.primary_keys)}")


if __name__ == "__main__":
    main()
