# tests/test_qdrant_connection.py

"""
Test script to verify Qdrant connection and vector operations.
Run this after starting Docker services.
"""

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from datetime import datetime
import uuid


def test_qdrant_connection():
    """Test basic Qdrant connectivity"""

    print("=" * 60)
    print("Testing Qdrant Connection")
    print("=" * 60)

    try:
        # Connection parameters
        client = QdrantClient(
            host="127.0.0.1",
            port=6333
        )

        collection_name = "educational_rag"
        vector_size = 1024

        # Test 1: Connection
        print("\n1. Testing connection...")

        collections = client.get_collections()

        print("   ✓ Connected successfully")

        # Test 2: List collections
        print("\n2. Listing collections...")

        existing_collections = collections.collections

        print(f"   ✓ Found {len(existing_collections)} collections")

        for collection in existing_collections:
            print(f"      - {collection.name}")

        # Test 3: Create collection
        print("\n3. Checking collection...")

        collection_names = [c.name for c in existing_collections]

        if collection_name not in collection_names:

            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )

            print(f"   ✓ Collection created: {collection_name}")

        else:
            print(f"   ✓ Collection already exists")

        # Test 4: Collection info
        print("\n4. Fetching collection info...")

        info = client.get_collection(collection_name)

        print(f"   Status: {info.status}")
        print(f"   Points count: {getattr(info, 'points_count', 0)}")

        print("   ✓ Collection info retrieved")

        # Test 5: Insert vector
        print("\n5. Testing vector insertion...")

        point_id = str(uuid.uuid4())

        sample_vector = [0.1] * vector_size

        client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=sample_vector,
                    payload={
                        "source": "test",
                        "type": "connection_test",
                        "timestamp": datetime.now().isoformat()
                    }
                )
            ]
        )

        print(f"   ✓ Vector inserted: {point_id}")

        # Test 6: Similarity search
        print("\n6. Testing similarity search...")

        results = client.query_points(
            collection_name=collection_name,
            query=sample_vector,
            limit=3
        ).points

        print(f"   ✓ Found {len(results)} result(s)")

        for result in results:
            print(f"      - ID: {result.id}")
            print(f"        Score: {result.score}")

        # Test 7: Payload filtering
        print("\n7. Testing payload filtering...")

        filtered_results = client.scroll(
            collection_name=collection_name,
            scroll_filter={
                "must": [
                    {
                        "key": "type",
                        "match": {
                            "value": "connection_test"
                        }
                    }
                ]
            },
            limit=5
        )

        print(f"   ✓ Filter query successful")

        # Test 8: Delete vector
        print("\n8. Cleaning up test vector...")

        client.delete(
            collection_name=collection_name,
            points_selector=[point_id]
        )

        print("   ✓ Test vector deleted")

        # Test 9: Final collection count
        print("\n9. Final collection status...")

        final_info = client.get_collection(collection_name)

        print(f"   Collection: {collection_name}")
        print(f"   Status: {final_info.status}")

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)

        return True

    except Exception as e:

        print(f"\n❌ Error: {e}")

        import traceback
        traceback.print_exc()

        print("\nTroubleshooting:")
        print("1. docker compose up -d")
        print("2. docker ps")
        print("3. Check Qdrant logs:")
        print("   docker logs educational_rag_qdrant")

        return False


if __name__ == "__main__":

    success = test_qdrant_connection()

    exit(0 if success else 1)