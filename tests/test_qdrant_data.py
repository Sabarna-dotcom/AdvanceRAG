"""
Quick Qdrant data check.
Shows all collections, how many vectors are in each,
and prints sample records.

Run with:
    python tests/test_qdrant_data.py
"""

from qdrant_client import QdrantClient

# ============================================
# Connect
# ============================================

client = QdrantClient(host="localhost", port=6333)

print("\n" + "=" * 60)
print("  QDRANT DATA CHECK")
print("=" * 60)

# ============================================
# Step 1: List all collections
# ============================================

print("\n📦 Collections found:")
print("-" * 40)

collections = client.get_collections().collections

if not collections:
    print("  ❌ No collections found! Data not indexed yet.")
else:
    for col in collections:
        print(f"  ✓ {col.name}")

# ============================================
# Step 2: Count vectors in each collection
# ============================================

print("\n📊 Vector counts per collection:")
print("-" * 40)

for col in collections:
    try:
        info = client.get_collection(col.name)

        count = info.points_count
        vector_size = info.config.params.vectors.size

        print(f"  ✓ {col.name}")
        print(f"      vectors    : {count}")
        print(f"      dimensions : {vector_size}")

    except Exception as e:
        print(f"  ✗ {col.name} → error: {e}")

# ============================================
# Step 3: Sample records from each collection
# ============================================

print("\n🔍 Sample records from each collection:")
print("-" * 40)

for col in collections:
    try:
        print(f"\n  Collection: {col.name}")

        records, _ = client.scroll(
            collection_name=col.name,
            limit=2,
            with_payload=True,
            with_vectors=False  # skip vectors to keep output clean
        )

        if not records:
            print("    ⚠ No records found.")
            continue

        for i, record in enumerate(records, 1):

            payload = record.payload or {}

            text = payload.get("text", "")[:100].replace("\n", " ")
            metadata = payload.get("metadata", {})

            source = metadata.get("source_name", "unknown")
            page = metadata.get("page_number", "-")

            chunk_id = payload.get("chunk_id", record.id)

            print(f"    [{i}] id       : {record.id}")
            print(f"         chunk_id : {chunk_id}")
            print(f"         source   : {source} | page: {page}")
            print(f"         text     : {text}...")
            print()

    except Exception as e:
        print(f"    ✗ Error reading {col.name}: {e}")

# ============================================
# Step 4: Final summary
# ============================================

print("=" * 60)
print("  SUMMARY")
print("=" * 60)

total_vectors = 0

for col in collections:
    try:
        info = client.get_collection(col.name)

        count = info.points_count
        total_vectors += count

        status = "✅ Has data" if count > 0 else "❌ Empty"

        print(f"  {status} | {col.name} ({count} vectors)")

    except Exception as e:
        print(f"  ✗ {col.name} → {e}")

print(f"\n  Total vectors across all collections: {total_vectors}")

if total_vectors > 0:
    print("\n  🎉 Qdrant has data — ready for retrieval!")
else:
    print("\n  ⚠ Qdrant is empty — run ingestion pipeline first.")

print("=" * 60)