# tests/test_postgres_connection.py

"""
Test script to verify PostgreSQL connection and pgvector extension.
Run this after starting Docker services.
"""

import psycopg2
from psycopg2.extras import Json
from datetime import datetime


def test_postgres_connection():
    """Test basic PostgreSQL connectivity"""

    print("=" * 60)
    print("Testing PostgreSQL Connection")
    print("=" * 60)

    try:
        # Updated connection parameters
        conn_params = {
            'host': '127.0.0.1',
            'port': 5433,
            'database': 'educational_rag',
            'user': 'raguser',
            'password': 'ragpassword'
        }

        # Test 1: Connect to database
        print("\n1. Testing connection...")

        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        cursor = conn.cursor()

        print("   ✓ Connected successfully")

        # Test 2: PostgreSQL version
        print("\n2. Checking PostgreSQL version...")

        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]

        print(f"   ✓ {version.split(',')[0]}")

        # Test 3: pgvector extension
        print("\n3. Checking pgvector extension...")

        cursor.execute("""
            SELECT * 
            FROM pg_extension 
            WHERE extname = 'vector';
        """)

        result = cursor.fetchone()

        if result:
            print("   ✓ pgvector extension installed")
        else:
            print("   ❌ pgvector extension missing")
            return False

        # Test 4: List tables
        print("\n4. Listing tables...")

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        tables = cursor.fetchall()

        print(f"   ✓ Found {len(tables)} tables")

        for table in tables:
            print(f"      - {table[0]}")

        # Test 5: Check conversations schema
        print("\n5. Checking conversations table...")

        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'conversations'
            ORDER BY ordinal_position;
        """)

        columns = cursor.fetchall()

        for col in columns:
            print(f"      - {col[0]}: {col[1]}")

        # Test 6: Insert test user first
        print("\n6. Creating test user...")

        cursor.execute("""
            INSERT INTO users (
                id,
                email,
                username,
                password_hash,
                full_name
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (
            'test_user_python',
            'python@test.com',
            'python_test_user',
            'dummy_hash',
            'Python Test User'
        ))

        print("   ✓ Test user ready")

        # Test 7: Insert conversation
        print("\n7. Testing INSERT...")

        cursor.execute("""
            INSERT INTO conversations (
                id,
                conversation_id,
                user_id,
                role,
                message,
                sources_used,
                metadata
            )
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
            Json({
                "test": True,
                "timestamp": datetime.now().isoformat()
            })
        ))

        result = cursor.fetchone()

        if result:
            print(f"   ✓ Inserted: {result[0]}")
        else:
            print("   ℹ Record already exists")

        # Test 8: SELECT query
        print("\n8. Testing SELECT...")

        cursor.execute("""
            SELECT
                id,
                conversation_id,
                user_id,
                role,
                message,
                timestamp
            FROM conversations
            WHERE user_id = 'test_user_python'
            LIMIT 3;
        """)

        rows = cursor.fetchall()

        print(f"   ✓ Found {len(rows)} record(s)")

        for row in rows:
            print(f"      - {row[0]} -> {row[4]}")

        # Test 9: JSONB query
        print("\n9. Testing JSONB query...")

        cursor.execute("""
            SELECT
                id,
                metadata->>'test'
            FROM conversations
            WHERE metadata ? 'test'
            LIMIT 1;
        """)

        result = cursor.fetchone()

        if result:
            print("   ✓ JSONB works")
            print(f"      ID: {result[0]}")

        # Test 10: Vector column
        print("\n10. Checking vector column...")

        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'conversations'
            AND column_name = 'embedding';
        """)

        result = cursor.fetchone()

        if result:
            print(f"   ✓ Vector column exists")

        # Test 11: Table counts
        print("\n11. Record counts...")

        tables_to_check = [
            'users',
            'conversations',
            'query_logs',
            'user_feedback',
            'system_metrics'
        ]

        for table in tables_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            print(f"   {table}: {count}")

        # Test 12: Indexes
        print("\n12. Checking indexes...")

        cursor.execute("""
            SELECT indexname, tablename
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """)

        indexes = cursor.fetchall()

        print(f"   ✓ Found {len(indexes)} indexes")

        # Cleanup
        cursor.close()
        conn.close()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)

        return True

    except psycopg2.OperationalError as e:

        print(f"\n❌ Connection Error: {e}")

        print("\nTroubleshooting:")
        print("1. docker compose up -d")
        print("2. docker ps")
        print("3. Wait for PostgreSQL initialization")
        print("4. Check logs:")
        print("   docker logs educational_rag_postgres")

        return False

    except Exception as e:

        print(f"\n❌ Error: {e}")

        import traceback
        traceback.print_exc()

        return False


if __name__ == "__main__":

    success = test_postgres_connection()

    exit(0 if success else 1)