# tests/test_redis_connection.py
"""
Test script to verify Redis connection is working.
Run this after starting Docker services.
"""

import redis
import json
from datetime import datetime


def test_redis_connection():
    """Test basic Redis connectivity"""
    print("=" * 60)
    print("Testing Redis Connection")
    print("=" * 60)

    try:
        # Connect to Redis
        r = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )

        # Test 1: Ping
        print("\n1. Testing PING...")
        response = r.ping()
        print(f"   ✓ PING successful: {response}")

        # Test 2: Set and Get
        print("\n2. Testing SET and GET...")
        test_key = "test:connection"
        test_value = "Redis is working!"
        r.set(test_key, test_value)
        retrieved = r.get(test_key)
        assert retrieved == test_value
        print(f"   ✓ SET/GET successful: {retrieved}")

        # Test 3: JSON storage (for cache)
        print("\n3. Testing JSON storage...")
        test_data = {
            "query": "What is photosynthesis?",
            "embedding": [0.1, 0.2, 0.3],
            "timestamp": datetime.now().isoformat()
        }
        r.set("test:json", json.dumps(test_data))
        retrieved_json = json.loads(r.get("test:json"))
        assert retrieved_json["query"] == test_data["query"]
        print(f"   ✓ JSON storage successful")
        print(f"   Data: {retrieved_json}")

        # Test 4: TTL (Time To Live)
        print("\n4. Testing TTL...")
        r.setex("test:ttl", 60, "This expires in 60 seconds")
        ttl = r.ttl("test:ttl")
        print(f"   ✓ TTL set successfully: {ttl} seconds remaining")

        # Test 5: Multiple keys
        print("\n5. Testing multiple keys...")
        r.mset({
            "test:key1": "value1",
            "test:key2": "value2",
            "test:key3": "value3"
        })
        keys = r.keys("test:key*")
        print(f"   ✓ Multiple keys created: {len(keys)} keys")
        print(f"   Keys: {keys}")

        # Test 6: Delete keys
        print("\n6. Cleaning up test keys...")
        test_keys = r.keys("test:*")
        if test_keys:
            r.delete(*test_keys)
            print(f"   ✓ Deleted {len(test_keys)} test keys")

        # Info
        print("\n7. Redis Info...")
        info = r.info()
        print(f"   Redis Version: {info.get('redis_version', 'N/A')}")
        print(f"   Used Memory: {info.get('used_memory_human', 'N/A')}")
        print(f"   Connected Clients: {info.get('connected_clients', 'N/A')}")

        print("\n" + "=" * 60)
        print("✅ ALL REDIS TESTS PASSED!")
        print("=" * 60)
        return True

    except redis.ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Docker is running")
        print("2. Run: docker-compose ps")
        print("3. Check if Redis container is up")
        print("4. Try: docker-compose up -d redis")
        return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = test_redis_connection()
    exit(0 if success else 1)