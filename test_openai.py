"""
Interactive test script for OpenAI integration
Run this to ask questions directly from the terminal
"""

import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

from openai_handler import process_chat_message
from memory import get_session_info, clear_session

def test_openai_integration():
    # Load environment variables
    load_dotenv()
    
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not found in .env file")
        return
    
    print("🔍 Testing OpenAI Integration...")
    print("-" * 50)
    
    # Test session ID
    test_session_id = "test-session-123"
    
    # Test cases
    test_cases = [
        "Hello! How are you doing?",  # Should use respond_directly
        "Show me all emails from Eric",  # Should generate SQL
        "What was the sentiment score?",  # Should reference previous context
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n{i}. Testing message: '{message}'")
        print("-" * 30)
        
        try:
            result = process_chat_message(message, test_session_id)
            
            print(f"Response: {result['response']}")
            print(f"Type: {result['type']}")
            
            if result['debug']['sql_query']:
                print(f"SQL Query: {result['debug']['sql_query']}")
                print(f"Results: {len(result['debug']['sql_results'] or [])} rows")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Check session info
    print(f"\nSession Info: {get_session_info(test_session_id)}")
    print("\n🎉 OpenAI testing complete!")

if __name__ == "__main__":
    test_openai_integration()