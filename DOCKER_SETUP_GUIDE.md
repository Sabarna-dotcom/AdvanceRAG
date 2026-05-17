# Docker Setup and Testing Guide
# Complete Step-by-Step Instructions for Redis and PostgreSQL

## Prerequisites
✓ Docker Desktop installed and running
✓ Python virtual environment activated
✓ All config files created from previous steps

---

## STEP 1: Verify Docker is Running

### Windows/Mac:
1. Open Docker Desktop application
2. Wait until it shows "Docker Desktop is running"

### Linux:
```bash
sudo systemctl status docker
```

---

## STEP 2: Navigate to Project Directory

```bash
cd AdvancedRAG_Project
```

Make sure you're in the root directory where `docker-compose.yml` is located.

---

## STEP 3: Start Docker Services

```bash
# Start both Redis and PostgreSQL in detached mode
docker-compose up -d
```

Expected output:
```
Creating network "advancedrag_project_rag_network" ... done
Creating volume "advancedrag_project_redis_data" ... done
Creating volume "advancedrag_project_postgres_data" ... done
Creating educational_rag_redis ... done
Creating educational_rag_postgres ... done
```

---

## STEP 4: Verify Containers are Running

```bash
# Check container status
docker-compose ps
```

You should see:
```
NAME                        STATUS        PORTS
educational_rag_postgres    Up (healthy)  0.0.0.0:5432->5432/tcp
educational_rag_redis       Up (healthy)  0.0.0.0:6379->6379/tcp
```

Both should show "Up" and "(healthy)" status.

---

## STEP 5: Wait for Initialization (Important!)

```bash
# Wait 10-15 seconds for PostgreSQL to initialize
# The first startup takes longer because it:
# - Creates the database
# - Installs pgvector extension
# - Runs init_db.sql script
# - Creates all tables

# Watch the logs to see initialization
docker-compose logs -f postgres
```

Look for: "database system is ready to accept connections"
Press `Ctrl+C` to exit logs.

---

## STEP 6: Test Redis Connection (Command Line)

```bash
# Test Redis using redis-cli
docker exec -it educational_rag_redis redis-cli ping
```

Expected output: `PONG`

```bash
# Test set and get
docker exec -it educational_rag_redis redis-cli set test "Hello Redis"
docker exec -it educational_rag_redis redis-cli get test
```

Expected output: `"Hello Redis"`

---

## STEP 7: Test PostgreSQL Connection (Command Line)

```bash
# Connect to PostgreSQL
docker exec -it educational_rag_postgres psql -U raguser -d educational_rag
```

Once connected, run these SQL commands:

```sql
-- Check pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

-- List all tables
\dt

-- Check conversations table
\d conversations

-- Count records
SELECT COUNT(*) FROM conversations;

-- Exit
\q
```

---

## STEP 8: Install Python Test Dependencies

```bash
# Make sure you're in your virtual environment
# Install required packages for testing

pip install redis psycopg2-binary
```

---

## STEP 9: Run Python Redis Test

```bash
# Run the Redis connection test
python tests/test_redis_connection.py
```

Expected output:
```
============================================================
Testing Redis Connection
============================================================

1. Testing PING...
   ✓ PING successful: True

2. Testing SET and GET...
   ✓ SET/GET successful: Redis is working!

3. Testing JSON storage...
   ✓ JSON storage successful
   Data: {'query': 'What is photosynthesis?', ...}

4. Testing TTL...
   ✓ TTL set successfully: 60 seconds remaining

5. Testing multiple keys...
   ✓ Multiple keys created: 3 keys
   Keys: ['test:key1', 'test:key2', 'test:key3']

6. Cleaning up test keys...
   ✓ Deleted 6 test keys

7. Redis Info...
   Redis Version: 7.x.x
   Used Memory: xxx KB
   Connected Clients: 1

============================================================
✅ ALL REDIS TESTS PASSED!
============================================================
```

---

## STEP 10: Run Python PostgreSQL Test

```bash
# Run the PostgreSQL connection test
python tests/test_postgres_connection.py
```

Expected output:
```
============================================================
Testing PostgreSQL Connection
============================================================

1. Testing connection...
   ✓ Connected successfully

2. Checking PostgreSQL version...
   ✓ PostgreSQL 16.x

3. Checking pgvector extension...
   ✓ pgvector extension is installed

4. Listing tables...
   ✓ Found 4 tables:
      - conversations
      - query_logs
      - system_metrics
      - user_feedback

5. Checking conversations table...
   ✓ Conversations table has 9 columns:
      - id: character varying
      - conversation_id: character varying
      - user_id: character varying
      - role: character varying
      - message: text
      - sources_used: jsonb
      - metadata: jsonb
      - timestamp: timestamp with time zone
      - embedding: vector

6. Testing INSERT...
   ✓ Inserted record with ID: test_python_001

7. Testing SELECT...
   ✓ Found 2 test record(s):
      - test_001: Test message to verify database setup...
      - test_python_001: Test from Python script...

8. Testing JSONB queries...
   ✓ JSONB query successful
      ID: test_python_001, test_value: True

9. Testing vector column...
   ✓ Vector column exists: embedding (vector)

10. Record counts...
   conversations: 2 records
   query_logs: 0 records
   user_feedback: 0 records
   system_metrics: 0 records

11. Checking indexes...
   ✓ Found X indexes

============================================================
✅ ALL POSTGRESQL TESTS PASSED!
============================================================
```

---

## STEP 11: Test From Your Config Files

Create a quick test script to verify your config files work:

```python
# tests/test_config_integration.py
from config.cache_config import get_config as get_cache_config
from config.embedding_config import get_config as get_embedding_config
import redis
import psycopg2

def test_configs():
    print("Testing configuration integration...")
    
    # Test Redis config
    print("\n1. Testing Redis config...")
    cache_config = get_cache_config()
    r = redis.Redis(
        host=cache_config.host,
        port=cache_config.port,
        db=cache_config.db,
        decode_responses=True
    )
    assert r.ping()
    print("   ✓ Redis config works!")
    
    # Test embedding config
    print("\n2. Testing embedding config...")
    embed_config = get_embedding_config()
    print(f"   Model: {embed_config.model_name}")
    print(f"   Dimension: {embed_config.dimension}")
    print(f"   Batch size: {embed_config.batch_size}")
    print("   ✓ Embedding config loaded!")
    
    print("\n✅ All config integrations successful!")

if __name__ == "__main__":
    test_configs()
```

Run it:
```bash
python tests/test_config_integration.py
```

---

## STEP 12: View Container Logs (If Issues)

```bash
# View Redis logs
docker-compose logs redis

# View PostgreSQL logs
docker-compose logs postgres

# Follow logs in real-time
docker-compose logs -f
```

---

## STEP 13: Stop Services (When Done Testing)

```bash
# Stop containers but keep data
docker-compose stop

# Stop and remove containers (keeps data volumes)
docker-compose down

# Stop and remove everything including data (CAUTION!)
docker-compose down -v
```

---

## Troubleshooting Common Issues

### Issue 1: Port Already in Use

**Error:** "port is already allocated"

**Solution:**
```bash
# Check what's using the port
# For port 6379 (Redis):
lsof -i :6379

# For port 5432 (PostgreSQL):
lsof -i :5432

# OR on Windows:
netstat -ano | findstr :6379
netstat -ano | findstr :5432

# Stop the conflicting service or change ports in docker-compose.yml
```

### Issue 2: Docker Daemon Not Running

**Error:** "Cannot connect to the Docker daemon"

**Solution:**
- Windows/Mac: Open Docker Desktop
- Linux: `sudo systemctl start docker`

### Issue 3: Permission Denied

**Error:** "permission denied while trying to connect"

**Solution (Linux):**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Issue 4: Container Unhealthy

```bash
# Check health status
docker-compose ps

# Check logs for errors
docker-compose logs postgres

# Restart the container
docker-compose restart postgres
```

### Issue 5: Database Not Initialized

```bash
# Check if init script ran
docker-compose logs postgres | grep "Database initialized"

# If not found, check for errors
docker-compose logs postgres | grep ERROR

# Recreate with fresh data
docker-compose down -v
docker-compose up -d
```

---

## Quick Command Reference

```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose stop

# Restart a service
docker-compose restart redis

# Remove everything
docker-compose down -v

# Execute command in container
docker exec -it educational_rag_redis redis-cli
docker exec -it educational_rag_postgres psql -U raguser -d educational_rag
```

---

## Success Checklist

After completing all steps, you should have:

- [✓] Docker containers running (redis and postgres)
- [✓] Redis responding to PING
- [✓] PostgreSQL accessible and initialized
- [✓] pgvector extension installed
- [✓] All 4 tables created (conversations, query_logs, user_feedback, system_metrics)
- [✓] Python can connect to Redis
- [✓] Python can connect to PostgreSQL
- [✓] Config files load correctly
- [✓] Test data inserted successfully

---

## What's Next?

After verifying Docker services work:

1. ✅ Create .env file with all API keys
2. ✅ Test embedding generation with HuggingFace API
3. ✅ Test Pinecone connection
4. ✅ Start building the ingestion pipeline (Day 6-10)

---

## Need Help?

If you encounter issues:
1. Check Docker Desktop is running
2. Review container logs: `docker-compose logs`
3. Verify ports are not in use
4. Ensure init_db.sql file exists in scripts/ folder
5. Try recreating containers: `docker-compose down -v && docker-compose up -d`
