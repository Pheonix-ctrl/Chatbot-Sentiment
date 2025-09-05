"""
Simple terminal interface to test the chat system
Type questions directly and see responses
"""

import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

from openai_handler import process_chat_message

def terminal_chat():
    print("Terminal Chat Interface")
    print("Type your questions below (type 'exit' to quit)")
    print("-" * 50)
    
    session_id = "terminal-session-001"
    
    while True:
        # Get user input
        question = input("\nYour question: ").strip()
        
        # Exit condition
        if question.lower() in ['exit', 'quit', 'bye']:
            print("Goodbye!")
            break
            
        if not question:
            continue
        
        try:
            # Process the question
            result = process_chat_message(question, session_id)
            
            # Show the response
            print(f"\nResponse: {result['response']}")
            
            # Show debug info if SQL was used
            if result['debug'].get('sql_query'):
                print(f"\nSQL Generated: {result['debug']['sql_query']}")
                print(f"Rows returned: {len(result['debug']['sql_results'] or [])}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    terminal_chat()