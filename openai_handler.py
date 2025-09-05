"""
OpenAI handler with function calling for SQL generation and conversation
Integrates with database and memory modules
"""

import os
import json
from typing import Dict, Any, List, Optional
import logging
from openai import OpenAI

from prompts import SYSTEM_PROMPT
from database import execute_sql, DatabaseError
from memory import (
    get_conversation_history, 
    add_user_message, 
    add_assistant_message,
)

logger = logging.getLogger(__name__)

class OpenAIHandler:
    """
    Handles OpenAI function calling for sentiment analytics
    Manages the complete conversation flow with memory and database integration
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY environment variable is required")
    
    def process_message(self, user_message: str, session_id: str) -> Dict[str, Any]:
        """
        Process a user message with full context and function calling
        
        Args:
            user_message: The user's input message
            session_id: Session identifier for memory management
            
        Returns:
            Dictionary with response and debug information
        """
        logger.info(f"🔍 Processing message for session {session_id[:8]}...")
        logger.info(f"📝 User Input: {user_message}")
        
        try:
            # Add user message to memory
            add_user_message(session_id, user_message)
            
            # Get conversation history for context
            conversation_history = get_conversation_history(session_id, limit=10)
            
            # Build messages for OpenAI
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
            
            # Add conversation history
            messages.extend(conversation_history[:-1])  # Exclude the just-added user message
            messages.append({"role": "user", "content": user_message})
            
            logger.info(f"💭 Including {len(conversation_history)} previous messages for context")
            
            # Define available functions
            functions = [
                {
                    "type": "function",
                    "function": {
                        "name": "execute_sql",
                        "description": "Execute a SQL query against the client sentiment database",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The SQL query to execute"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "respond_directly",
                        "description": "Respond conversationally without executing any database queries",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "The conversational response"
                                }
                            },
                            "required": ["message"]
                        }
                    }
                }
            ]
            
            # Make the OpenAI call
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=functions,
                tool_choice="auto",
                temperature=0.7
            )
            
            assistant_message = response.choices[0].message
            
            # Handle function calls
            if assistant_message.tool_calls:
                return self._handle_function_call(assistant_message, session_id)
            else:
                # Direct response without function call
                content = assistant_message.content or "I didn't quite understand that. Could you try rephrasing?"
                add_assistant_message(session_id, content)
                
                logger.info(f"✅ Direct response: {content[:100]}...")
                return {
                    "response": content,
                    "type": "direct",
                    "debug": {
                        "function_called": None,
                        "sql_query": None,
                        "sql_results": None
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            error_response = "Sorry, I encountered an error processing your request. Please try again."
            add_assistant_message(session_id, error_response)
            
            return {
                "response": error_response,
                "type": "error",
                "debug": {
                    "error": str(e),
                    "function_called": None,
                    "sql_query": None,
                    "sql_results": None
                }
            }
    
    def _handle_function_call(self, assistant_message, session_id: str) -> Dict[str, Any]:
        """Handle OpenAI function calls"""
        tool_call = assistant_message.tool_calls[0]
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        logger.info(f"🤖 OpenAI Function Call: {function_name}")
        
        if function_name == "execute_sql":
            return self._execute_sql_function(function_args, session_id, tool_call.id)
        elif function_name == "respond_directly":
            return self._respond_directly_function(function_args, session_id)
        else:
            logger.error(f"Unknown function called: {function_name}")
            error_response = "I encountered an unexpected error. Please try again."
            add_assistant_message(session_id, error_response)
            return {
                "response": error_response,
                "type": "error",
                "debug": {"error": f"Unknown function: {function_name}"}
            }
    
    def _execute_sql_function(self, function_args: Dict, session_id: str, tool_call_id: str) -> Dict[str, Any]:
        """Execute SQL and get formatted response"""
        sql_query = function_args.get("query", "")
        logger.info(f"📊 Generated SQL: {sql_query}")
        
        try:
            # Execute the SQL query
            sql_results = execute_sql(sql_query)
            logger.info(f"💾 Database Results: {len(sql_results)} rows returned")
            
            # Create the tool response for OpenAI
            tool_response = {
                "tool_call_id": tool_call_id,
                "output": json.dumps(sql_results, default=str, indent=2)
            }
            
            # Get the formatted response from OpenAI
            formatted_response = self._get_formatted_response(sql_results, session_id, tool_response)
            
            # Save to memory with metadata
            add_assistant_message(
                session_id, 
                formatted_response,
                sql_query=sql_query,
                sql_results=sql_results
            )
            
            logger.info(f"✅ Final Response: {formatted_response[:100]}...")
            
            return {
                "response": formatted_response,
                "type": "sql_analysis",
                "debug": {
                    "function_called": "execute_sql",
                    "sql_query": sql_query,
                    "sql_results": sql_results,
                    "result_count": len(sql_results)
                }
            }
            
        except DatabaseError as e:
            logger.error(f"❌ Database Error: {e}")
            error_response = f"I encountered a database error: {str(e)}"
            add_assistant_message(session_id, error_response)
            
            return {
                "response": error_response,
                "type": "database_error",
                "debug": {
                    "function_called": "execute_sql",
                    "sql_query": sql_query,
                    "sql_results": None,
                    "error": str(e)
                }
            }
    
    def _respond_directly_function(self, function_args: Dict, session_id: str) -> Dict[str, Any]:
        """Handle direct conversational response"""
        response_message = function_args.get("message", "")
        logger.info(f"💬 Direct Response: {response_message[:100]}...")
        
        add_assistant_message(session_id, response_message)
        
        return {
            "response": response_message,
            "type": "conversational",
            "debug": {
                "function_called": "respond_directly",
                "sql_query": None,
                "sql_results": None
            }
        }
    
    def _get_formatted_response(self, sql_results: List[Dict], session_id: str, tool_response: Dict) -> str:
        """Get formatted response from OpenAI after SQL execution"""
        try:
            # Create a follow-up call to format the results
            format_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "Format these SQL results into a natural language response:"},
                {"role": "assistant", "content": None, "tool_calls": [
                    {"id": tool_response["tool_call_id"], "type": "function", "function": {"name": "execute_sql", "arguments": "{}"}}
                ]},
                {"role": "tool", "content": tool_response["output"], "tool_call_id": tool_response["tool_call_id"]}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=format_messages,
                temperature=0.7
            )
            
            return response.choices[0].message.content or "I couldn't format the results properly."
            
        except Exception as e:
            logger.error(f"Error formatting results: {e}")
            # Fallback to basic formatting
            if not sql_results:
                return "No matching results found."
            elif len(sql_results) == 1 and len(sql_results[0]) == 1:
                # Single value result
                value = list(sql_results[0].values())[0]
                return f"Result: {value}"
            else:
                return f"Found {len(sql_results)} results. {json.dumps(sql_results[:3], default=str, indent=2)}"


# Global handler instance
openai_handler = OpenAIHandler()


# Convenience function
def process_chat_message(user_message: str, session_id: str) -> Dict[str, Any]:
    """Process a chat message and return formatted response"""
    return openai_handler.process_message(user_message, session_id)