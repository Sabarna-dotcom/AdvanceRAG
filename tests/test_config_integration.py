# tests/test_config_integration.py
"""
Test that config files correctly integrate with Redis and PostgreSQL.
This validates the entire configuration system works end-to-end.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.cache_config import get_config as get_cache_config
from src.config.embedding_config import get_config as get_embedding_config
from src.config.settings import get_settings
import redis
import psycopg2
from psycopg2.extras import Json


def test_config_integration():
    """Test all config integrations"""
    print("=" * 60)
    print("Testing Configuration Integration")
    print("=" * 60)

    try:
        # Test 1: Load main settings
        print("\n1. Loading main settings...")
        settings = get_settings()
        print(f"   ✓ App environment: {settings.app_env}")
        print(f"   ✓ Debug mode: {settings.debug}")
        print(f"   ✓ Log level: {settings.log_level}")

        # Test 2: Redis config and connection
        print("\n2. Testing Redis configuration...")
        cache_config = get_cache_config()
        print(f"   Host: {cache_config.host}")
        print(f"   Port: {cache_config.port}")
        print(f"   DB: {cache_config.db}")
        print(f"   Query TTL: {cache_config.ttl_query}s")

        print("\n   Connecting to Redis...")
        r = redis.Redis(
            host=cache_config.host,
            port=cache_config.port,
            password=cache_config.password if cache_config.password else None,
            db=cache_config.db,
            decode_responses=True
        )
        assert r.ping()
        print("   ✓ Redis connection successful!")

        # Test cache operations with config
        test_key = "config_test:query"
        test_value = "test_value"
        r.setex(test_key, cache_config.ttl_query, test_value)
        retrieved = r.get(test_key)
        assert retrieved == test_value
        print(f"   ✓ Cache TTL working: {r.ttl(test_key)}s remaining")
        r.delete(test_key)

        # Test 3: Embedding config
        print("\n3. Testing Embedding configuration...")
        embed_config = get_embedding_config()
        print(f"   Model: {embed_config.model_name}")
        print(f"   Dimension: {embed_config.dimension}")
        print(f"   Batch size: {embed_config.batch_size}")
        print(f"   Max retries: {embed_config.max_retries}")
        print("   ✓ Embedding config loaded!")

        # Test 4: Database config (from settings)
        print("\n4. Testing Database configuration...")
        print(f"   Database URL: {settings.database_url[:30]}...")
        print(f"   Pool size: {settings.database_pool_size}")
        print(f"   Max overflow: {settings.database_max_overflow}")

        print("\n   Connecting to PostgreSQL...")
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   ✓ PostgreSQL connected: {version.split(',')[0]}")

        # Test insert using config-loaded connection
        # Create test user first
        cursor.execute("""
            INSERT INTO users (
                id,
                email,
                username,
                password_hash,
                full_name,
                is_active,
                is_verified
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (
            'test_user_config',
            'config@test.com',
            'config_test_user',
            'dummy_password_hash',
            'Config Test User',
            True,
            True
        ))

        conn.commit()

        print("   ✓ Test user created")

        cursor.execute("""
            INSERT INTO conversations 
            (id, conversation_id, user_id, role, message, sources_used, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            RETURNING id;
        """, (
            'config_test_001',
            'conv_config_test',
            'test_user_config',
            'user',
            'Test from config integration',
            Json([]),
            Json({})
        ))
        conn.commit()
        print("   ✓ Database write successful!")

        cursor.close()
        conn.close()

        # Test 5: Retrieval config
        print("\n5. Testing Retrieval configuration...")
        from src.config.retrieval_config import get_config as get_retrieval_config
        retrieval_config = get_retrieval_config()
        print(f"   Top-k initial: {retrieval_config.top_k_initial}")
        print(f"   Top-k final: {retrieval_config.top_k_final}")
        print(f"   Use HyDE: {retrieval_config.use_hyde}")
        print(f"   Use Fusion: {retrieval_config.use_fusion}")
        print("   ✓ Retrieval config loaded!")

        # Test 6: LLM config
        print("\n6. Testing LLM configuration...")
        from src.config.llm_config import get_config as get_llm_config
        llm_config = get_llm_config()
        print(f"   Model: {llm_config.model_name}")
        print(f"   Temperature: {llm_config.temperature}")
        print(f"   Max tokens: {llm_config.max_tokens}")
        print(f"   Track costs: {llm_config.track_costs}")
        print("   ✓ LLM config loaded!")

        # Test 7: Guardrails config
        print("\n7. Testing Guardrails configuration...")
        from src.config.guardrails_config import get_config as get_guardrails_config
        guardrails_config = get_guardrails_config()
        print(f"   Max query length: {guardrails_config.input.max_query_length}")
        print(f"   Min query length: {guardrails_config.input.min_query_length}")
        print(f"   Hallucination detection: {guardrails_config.output.enable_hallucination_detection}")
        print(f"   Rate limit (hour): {guardrails_config.rate_limit.per_user_hour}")
        print("   ✓ Guardrails config loaded!")

        # Test 8: Data Ingestion config
        print("\n8. Testing Data Ingestion configuration...")
        from src.config.ingestion_config import get_config as get_ingestion_config
        ingestion_config = get_ingestion_config()

        print(f"   PDF chunk size: "f"{ingestion_config.pdf.chunk_size}")
        print(f"   PDF overlap: "f"{ingestion_config.pdf.chunk_overlap}")
        print(f"   PDF parent size: "f"{ingestion_config.pdf.parent_size}")
        print(f"   PDF child size: "f"{ingestion_config.pdf.child_size}")

        print(f"   Raw PDF dir: "f"{ingestion_config.paths.raw_pdf_dir}")
        print(f"   Processed PDF dir: "f"{ingestion_config.paths.processed_pdf_dir}")
        print(f"   Raw Audio dir: "f"{ingestion_config.paths.raw_audio_dir}")
        print(f"   Processed Transcript dir: "f"{ingestion_config.paths.processed_transcript_dir}")
        print(f"   Raw VIDEO dir: "f"{ingestion_config.paths.raw_video_dir}")
        print("   ✓ Data Ingestion config loaded!")

        # Test 9: Vector Store configuration...
        print("\n9. Testing Vector Store configuration...")
        from src.config.vectorstore_config import get_config as get_vectorstore_config
        vectorstore_config = get_vectorstore_config()
        print(f"   Qdrant host: {vectorstore_config.host}")
        print(f"   Qdrant port: {vectorstore_config.port}")
        print(f"   Qdrant gRPC port: {vectorstore_config.grpc_port}")
        print(f"   Collection name: {vectorstore_config.collection_name}")
        print(f"   Vector size: {vectorstore_config.vector_size}")
        print(f"   Distance metric: {vectorstore_config.distance}")
        print(f"   PDF Collection: {vectorstore_config.pdf_collection}")
        print(f"   Video Collection: {vectorstore_config.video_collection}")
        print("   ✓ Vector Store config loaded!")

        # Test 10: Auth config
        print("\n10. Testing Authentication configuration...")
        from src.config.auth_config import get_config as get_auth_config
        auth_config = get_auth_config()
        print(f"   JWT Algorithm: {auth_config.jwt_algorithm}")
        print(f"   Access token expiry: {auth_config.access_token_expire_minutes} min")
        print(f"   Refresh token expiry: {auth_config.refresh_token_expire_days} days")

        print(f"   Password min length: {auth_config.password_min_length}")
        print(f"   Require special chars: {auth_config.password_require_special}")
        print(f"   Require numbers: {auth_config.password_require_numbers}")
        print(f"   Require uppercase: {auth_config.password_require_uppercase}")

        print(f"   Max sessions/user: {auth_config.max_sessions_per_user}")
        print(f"   Session timeout: {auth_config.session_timeout_minutes} min")

        print(f"   2FA enabled: {auth_config.enable_2fa}")
        print(f"   Max login attempts: {auth_config.max_login_attempts}")
        print(f"   Lockout duration: {auth_config.lockout_duration_minutes} min")

        print("   ✓ Authentication config loaded!")

        print("\n" + "=" * 60)
        print("✅ ALL CONFIGURATION INTEGRATION TESTS PASSED!")
        print("=" * 60)
        print("\nSummary:")
        print("  • Main settings loaded from .env")
        print("  • Redis connection via cache_config ✓")
        print("  • PostgreSQL connection via settings ✓")
        print("  • All module configs loading correctly ✓")
        print("  • Ready for development!")

        return True

    except FileNotFoundError as e:
        print(f"\n❌ File not found: {e}")
        print("\nMake sure .env file exists in project root!")
        print("Copy .env.example to .env and fill in your API keys.")
        return False

    except redis.ConnectionError as e:
        print(f"\n❌ Redis connection failed: {e}")
        print("\nMake sure Docker containers are running:")
        print("  docker-compose up -d")
        return False

    except psycopg2.OperationalError as e:
        print(f"\n❌ PostgreSQL connection failed: {e}")
        print("\nMake sure Docker containers are running:")
        print("  docker-compose up -d")
        print("  docker-compose logs postgres")
        return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_config_integration()
    exit(0 if success else 1)