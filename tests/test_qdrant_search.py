"""
Quick Qdrant search diagnostic.
Run: python -m tests.test_qdrant_search

Tests:
    1. Can connect to Qdrant
    2. Lists all collections + point counts
    3. Prints a sample payload from each collection
    4. Does a raw vector search using whatever API is available
    5. Does an Ollama embedding + real search end-to-end
"""

import sys

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
TEST_QUERY = "biotechnology and its applications"


def sep(title=""):
    print(f"\n{'='*60}")
    if title:
        print(f"  {title}")
    print(f"{'='*60}")


# ============================================================
# 1. Connection
# ============================================================
sep("TEST 1: Qdrant connection")

try:
    from qdrant_client import QdrantClient

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # simple health check
    info = client.get_collections()

    print(f"  OK  Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")

except Exception as e:
    print(f"  FAIL  Cannot connect: {e}")
    sys.exit(1)


# ============================================================
# 2. List collections
# ============================================================
sep("TEST 2: Collections")

collections = info.collections

if not collections:
    print("  WARNING  No collections found in Qdrant!")
    print("            Data may not have been ingested yet.")

for col in collections:
    try:
        count = client.count(collection_name=col.name)

        print(
            f"  Collection: {col.name!r:40s} points: {count.count}"
        )

    except Exception as e:
        print(
            f"  Collection: {col.name!r:40s} (count failed: {e})"
        )


# ============================================================
# 3. Sample payload from each collection
# ============================================================
sep("TEST 3: Sample payload")

for col in collections:

    try:
        # scroll returns (points, next_offset)
        points, _ = client.scroll(
            collection_name=col.name,
            limit=1,
            with_payload=True,
            with_vectors=False,
        )

        if points:
            p = points[0]

            payload = p.payload or {}

            text_preview = str(
                payload.get("text", payload)
            )[:200]

            print(f"\n [{col.name}] id={p.id}")
            print(f"  payload keys : {list(payload.keys())}")
            print(f"  text preview : {text_preview}")

        else:
            print(f"  [{col.name}] no points found")

    except Exception as e:
        print(f"  [{col.name}] scroll failed: {e}")


# ============================================================
# 4. Detect available search API
# ============================================================
sep("TEST 4: Detect search API")

has_query_points = hasattr(client, "query_points")
has_search = hasattr(client, "search")

print(f"  query_points() available : {has_query_points}")
print(f"  search()       available : {has_search}")

import qdrant_client as _qc

try:
    from importlib.metadata import version as _pkg_version

    _qc_ver = _pkg_version("qdrant-client")

except Exception:
    _qc_ver = getattr(_qc, "__version__", "unknown")

print(f"  qdrant-client version    : {_qc_ver}")

# ============================================================
# 5. Real embedding + search
# ============================================================
sep("TEST 5: Embedding + search")

if not collections:
    print("  SKIP  No collections to search.")
    sys.exit(0)

# --- embed query via Ollama ---
print(f"  Embedding query: '{TEST_QUERY}'")

try:
    import requests

    resp = requests.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "bge-m3",
            "prompt": TEST_QUERY,
        },
        timeout=30,
    )

    resp.raise_for_status()

    vector = resp.json()["embedding"]

    print(f"  Embedding dim: {len(vector)}")

except Exception as e:
    print(f"  FAIL  Ollama embedding failed: {e}")
    sys.exit(1)


# --- search each collection ---
for col in collections:

    print(f"\n Searching '{col.name}' ...")

    try:

        if has_query_points:

            result = client.query_points(
                collection_name=col.name,
                query=vector,
                limit=3,
                with_payload=True,
            )

            hits = result.points

        else:

            hits = client.search(
                collection_name=col.name,
                query_vector=vector,
                limit=3,
            )

        if not hits:
            print(
                "  WARNING  0 results - collection may be empty "
                "or vector dim mismatch."
            )

        for i, hit in enumerate(hits, 1):

            text = (
                (hit.payload or {}).get(
                    "text",
                    "<no text field>"
                )
            )

            print(
                f"  [{i}] score={hit.score:.4f} "
                f"text='{str(text)[:120]}'"
            )

    except Exception as e:
        print(f"  FAIL  Search error: {e}")

print("\nDone.")