"""
Quick test to verify Ollama embedding is working correctly.
Run this first before running full retrieval tests.

    python tests/test_embedding_quick.py
"""

import ollama

print("=" * 50)
print("  OLLAMA EMBEDDING QUICK CHECK")
print("=" * 50)

# Step 1: Check Ollama connection
print("\n1. Checking Ollama connection...")
try:
    client = ollama.Client(host="http://localhost:11434")
    models = client.list()

    print("✓ Ollama is running")

except Exception as e:
    print(f"✗ Ollama not reachable: {e}")
    print("  Make sure Ollama is running")
    exit(1)

# Step 2: Check available models
print("\n2. Available models:")
try:
    for model in models.get("models", []):
        name = model.get("name", model.get("model", "unknown"))
        print(f"  - {name}")

except Exception as e:
    print(f"  ✗ Could not list models: {e}")

# Step 3: Test embedding with bge-m3
print("\n3. Testing embedding with bge-m3...")
try:
    response = client.embeddings(
        model="bge-m3",
        prompt="What is photosynthesis?"
    )

    print(f"  Response type: {type(response)}")
    print(
        f"  Response keys/attrs: "
        f"{dir(response) if hasattr(response, '__dict__') else response.keys() if isinstance(response, dict) else 'N/A'}"
    )

    # Try both formats
    if hasattr(response, "embedding"):
        embedding = response.embedding
        print("  ✓ Got embedding via response.embedding")

    elif isinstance(response, dict):
        embedding = response.get("embedding")
        print("  ✓ Got embedding via response['embedding']")

    else:
        embedding = None

    if embedding:
        print(f"  ✓ Embedding dimension: {len(embedding)}")
        print(f"  ✓ First 5 values: {embedding[:5]}")
    else:
        print("  ✗ Embedding is empty!")

except Exception as e:
    print(f"  ✗ Embedding failed: {e}")
    print("  → Try: ollama pull bge-m3")

# Step 4: Test via your embedding model class
print("\n4. Testing via OllamaEmbeddingModel class...")

try:
    from src.embeddings.embedding_model import OllamaEmbeddingModel

    embedder = OllamaEmbeddingModel()

    result = embedder.embed(["What is photosynthesis?"])

    if result and len(result) > 0:
        print(f"  ✓ Class embed works! Dimension: {len(result[0])}")
    else:
        print("  ✗ Class embed returned empty list")

except Exception as e:
    print(f"  ✗ Class embed failed: {e}")

print("\n" + "=" * 50)