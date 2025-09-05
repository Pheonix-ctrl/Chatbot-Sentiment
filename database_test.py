"""
Test script for database connectivity and basic operations
Run this to verify your Supabase connection is working
"""

import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

from database import execute_sql, test_database_connection, get_table_structure

def main():
    print("🔍 Testing Supabase Database Connection...")
    print("-" * 50)
    
    # Test basic connection
    print("1. Testing connection...")
    if test_database_connection():
        print("✅ Database connection successful!")
    else:
        print("❌ Database connection failed!")
        return
    
    # Test table structure queries
    print("\n2. Testing table structure queries...")
    tables = ['openphone_gmail_ai', 'openphone_call_ai', 'openphone_text_ai']
    
    for table in tables:
        try:
            columns = get_table_structure(table)
            if columns:
                print(f"✅ Table '{table}' found with {len(columns)} columns")
                # Show first few columns
                for col in columns[:3]:
                    print(f"   - {col['column_name']} ({col['data_type']})")
                if len(columns) > 3:
                    print(f"   - ... and {len(columns) - 3} more columns")
            else:
                print(f"⚠️  Table '{table}' not found or has no columns")
        except Exception as e:
            print(f"❌ Error accessing table '{table}': {e}")
    
    # Test simple SELECT query
    print("\n3. Testing simple SELECT queries...")
    test_queries = [
        "SELECT COUNT(*) as total_emails FROM \"openphone_gmail_ai\" LIMIT 1",
        "SELECT COUNT(*) as total_calls FROM \"openphone_call_ai\" LIMIT 1", 
        "SELECT COUNT(*) as total_texts FROM \"openphone_text_ai\" LIMIT 1"
    ]
    
    for query in test_queries:
        try:
            result = execute_sql(query)
            table_name = query.split('FROM "')[1].split('"')[0]
            count = result[0] if result else {'total': 0}
            print(f"✅ {table_name}: {count}")
        except Exception as e:
            print(f"❌ Query failed: {e}")
    
    # Test SQL safety validation
    print("\n4. Testing SQL safety validation...")
    dangerous_queries = [
        "DROP TABLE test",
        "DELETE FROM openphone_gmail_ai",
        "INSERT INTO test VALUES (1)"
    ]
    
    for query in dangerous_queries:
        try:
            execute_sql(query)
            print(f"❌ Dangerous query was allowed: {query}")
        except Exception as e:
            print(f"✅ Dangerous query blocked: {query}")
    
    print("\n🎉 Database testing complete!")

if __name__ == "__main__":
    main()