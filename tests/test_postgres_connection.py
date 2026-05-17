# tests/test_postgres_connection.py
"""
Test script to verify PostgreSQL connection and pgvector extension.
Run this after starting Docker services.
"""

import psycopg2
from psycopg2.extras import Json
import json
from datetime import datetime


def test_postgres_connection():
    """Test basic PostgreSQL connectivity"""
    print("=" * 60)
    print("Testing PostgreSQL Connection")
    print("=" * 60)

    try:
        # Connection parameters
        conn_params = {
            'host': '127.0.0.1',
            'port': 5433,
            'database': 'educational_rag',
            'user': 'postgres',
            'password': 'postgres'
        }

        # Test 1: Connect to database
        print("\n1. Testing connection...")
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        cursor = conn.cursor()
        print("   ✓ Connected successfully")

        # Test 2: Check PostgreSQL version
        print("\n2. Checking PostgreSQL version...")
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   ✓ {version.split(',')[0]}")

        # Test 3: Check pgvector extension
        print("\n3. Checking pgvector extension...")
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        result = cursor.fetchone()
        if result:
            print("   ✓ pgvector extension is installed")
        else:
            print("   ❌ pgvector extension NOT found")
            return False

        # Test 4: List all tables
        print("\n4. Listing tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"   ✓ Found {len(tables)} tables:")
        for table in tables:
            print(f"      - {table[0]}")

        # Test 5: Check conversations table structure
        print("\n5. Checking conversations table...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'conversations'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        print(f"   ✓ Conversations table has {len(columns)} columns:")
        for col in columns:
            print(f"      - {col[0]}: {col[1]}")

        # Test 6: Insert test data
        print("\n6. Testing INSERT...")
        cursor.execute("""
            INSERT INTO conversations 
            (id, conversation_id, user_id, role, message, sources_used, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            RETURNING id;
        """, (
            'test_python_001',
            'conv_test_python',
            'test_user_python',
            'user',
            'Test from Python script',
            Json([{"source": "test", "page": 1}]),
            Json({"test": True, "timestamp": datetime.now().isoformat()})
        ))
        result = cursor.fetchone()
        if result:
            print(f"   ✓ Inserted record with ID: {result[0]}")
        else:
            print("   ℹ Record already exists (skipped)")

        # Test 7: Query test data
        print("\n7. Testing SELECT...")
        cursor.execute("""
            SELECT id, conversation_id, user_id, role, message, timestamp
            FROM conversations
            WHERE user_id LIKE 'test%'
            LIMIT 3;
        """)
        rows = cursor.fetchall()
        print(f"   ✓ Found {len(rows)} test record(s):")
        for row in rows:
            print(f"      - {row[0]}: {row[4][:50]}...")

        # Test 8: Test JSONB queries
        print("\n8. Testing JSONB queries...")
        cursor.execute("""
            SELECT id, metadata->>'test' as test_value
            FROM conversations
            WHERE metadata ? 'test'
            LIMIT 1;
        """)
        result = cursor.fetchone()
        if result:
            print(f"   ✓ JSONB query successful")
            print(f"      ID: {result[0]}, test_value: {result[1]}")

        # Test 9: Test vector column (if data exists)
        print("\n9. Testing vector column...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'conversations' 
            AND column_name = 'embedding';
        """)
        result = cursor.fetchone()
        if result:
            print(f"   ✓ Vector column exists: {result[0]} ({result[1]})")

        # Test 10: Count records in each table
        print("\n10. Record counts...")
        for table in ['conversations', 'query_logs', 'user_feedback', 'system_metrics']:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            print(f"   {table}: {count} records")

        # Test 11: Check indexes
        print("\n11. Checking indexes...")
        cursor.execute("""
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """)
        indexes = cursor.fetchall()
        print(f"   ✓ Found {len(indexes)} indexes")

        # Close connection
        cursor.close()
        conn.close()

        print("\n" + "=" * 60)
        print("✅ ALL POSTGRESQL TESTS PASSED!")
        print("=" * 60)
        return True

    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Docker is running")
        print("2. Run: docker-compose ps")
        print("3. Check if PostgreSQL container is up")
        print("4. Try: docker-compose up -d postgres")
        print("5. Wait 10 seconds for initialization")
        return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_postgres_connection()
    exit(0 if success else 1)