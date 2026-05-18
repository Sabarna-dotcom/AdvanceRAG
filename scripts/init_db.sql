-- scripts/init_db.sql
-- Updated Database Schema with Authentication and Memory Management
-- This runs automatically when PostgreSQL container starts for the first time

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- AUTHENTICATION TABLES
-- ============================================

-- Users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- User sessions for JWT token management
CREATE TABLE IF NOT EXISTS user_sessions (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    device_info JSONB,
    ip_address VARCHAR(50),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);

-- ============================================
-- CONVERSATION & CHAT HISTORY (Short-term Memory)
-- ============================================

-- Conversations table - stores individual messages
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(50) PRIMARY KEY,
    conversation_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    message TEXT NOT NULL,
    sources_used JSONB,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    embedding vector(1024)  -- For semantic search of chat history
);

CREATE INDEX IF NOT EXISTS idx_conversations_conversation_id ON conversations(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_user_conv ON conversations(user_id, conversation_id);

-- Conversation metadata - stores conversation-level info
CREATE TABLE IF NOT EXISTS conversation_metadata (
    conversation_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    summary TEXT,
    topic VARCHAR(100),
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP WITH TIME ZONE,
    is_archived BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_conv_metadata_user ON conversation_metadata(user_id);
CREATE INDEX IF NOT EXISTS idx_conv_metadata_updated ON conversation_metadata(updated_at DESC);

-- ============================================
-- LONG-TERM MEMORY (User Profile & Learning)
-- ============================================

-- User long-term memory - stores user preferences and learning patterns
CREATE TABLE IF NOT EXISTS user_memory (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE UNIQUE,

    -- Learning preferences
    preferred_topics JSONB DEFAULT '[]'::jsonb,  -- ["photosynthesis", "physics", ...]
    learning_level VARCHAR(50) DEFAULT 'intermediate',  -- beginner, intermediate, advanced
    learning_style VARCHAR(50),  -- visual, textual, interactive

    -- Interaction patterns
    frequent_query_types JSONB DEFAULT '{}'::jsonb,  -- {"explanation": 45, "comparison": 30, ...}
    preferred_source_types JSONB DEFAULT '[]'::jsonb,  -- ["video", "pdf"]
    avg_session_duration INTEGER,  -- in minutes

    -- Engagement metrics
    total_queries INTEGER DEFAULT 0,
    total_conversations INTEGER DEFAULT 0,
    helpful_responses INTEGER DEFAULT 0,
    not_helpful_responses INTEGER DEFAULT 0,

    -- Personalization
    custom_preferences JSONB DEFAULT '{}'::jsonb,  -- {"theme": "dark", "language": "en"}

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_memory_user_id ON user_memory(user_id);

-- Topic interest tracking - what topics user has explored
CREATE TABLE IF NOT EXISTS user_topic_interest (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    topic VARCHAR(200) NOT NULL,
    interest_score FLOAT DEFAULT 1.0,  -- Increases with repeated queries
    first_queried_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_queried_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    query_count INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_topic_interest_user ON user_topic_interest(user_id);
CREATE INDEX IF NOT EXISTS idx_topic_interest_score ON user_topic_interest(user_id, interest_score DESC);

-- Conversation summaries - long-term compressed memory
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    conversation_id VARCHAR(50),
    summary_text TEXT NOT NULL,
    key_topics JSONB DEFAULT '[]'::jsonb,
    insights_learned JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    summary_embedding vector(1024)  -- For semantic search of past learnings
);

CREATE INDEX IF NOT EXISTS idx_conv_summaries_user ON conversation_summaries(user_id);
CREATE INDEX IF NOT EXISTS idx_conv_summaries_created ON conversation_summaries(created_at DESC);

-- ============================================
-- QUERY LOGS & ANALYTICS
-- ============================================

CREATE TABLE IF NOT EXISTS query_logs (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE SET NULL,
    conversation_id VARCHAR(50),
    query TEXT NOT NULL,
    response TEXT,
    retrieval_strategy VARCHAR(50),
    retrieval_confidence FLOAT,
    retrieval_count INTEGER,
    sources_used JSONB,
    latency_ms INTEGER,
    cost_usd FLOAT,
    ragas_scores JSONB,
    cache_hit BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_query_logs_user_id ON query_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_query_logs_conv ON query_logs(conversation_id);

-- User feedback on responses
CREATE TABLE IF NOT EXISTS user_feedback (
    id VARCHAR(50) PRIMARY KEY,
    query_log_id VARCHAR(50) REFERENCES query_logs(id) ON DELETE CASCADE,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    conversation_id VARCHAR(50),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_type VARCHAR(20) CHECK (feedback_type IN ('helpful', 'not_helpful', 'incorrect', 'incomplete', 'excellent')),
    comment TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_query_log_id ON user_feedback(query_log_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON user_feedback(user_id);

-- ============================================
-- SYSTEM METRICS
-- ============================================

CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE SET NULL,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name);

-- ============================================
-- TRIGGERS FOR AUTO-UPDATING
-- ============================================

-- Update conversation metadata count
CREATE OR REPLACE FUNCTION update_conversation_metadata()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO conversation_metadata (conversation_id, user_id, message_count, last_message_at)
    VALUES (NEW.conversation_id, NEW.user_id, 1, NEW.timestamp)
    ON CONFLICT (conversation_id) DO UPDATE
    SET message_count = conversation_metadata.message_count + 1,
        last_message_at = NEW.timestamp,
        updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_conversation_metadata
AFTER INSERT ON conversations
FOR EACH ROW EXECUTE FUNCTION update_conversation_metadata();

-- Update user memory query count
CREATE OR REPLACE FUNCTION update_user_memory_queries()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_memory (id, user_id, total_queries)
    VALUES (gen_random_uuid()::text, NEW.user_id, 1)
    ON CONFLICT (user_id) DO UPDATE
    SET total_queries = user_memory.total_queries + 1,
        updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_user_memory
AFTER INSERT ON query_logs
FOR EACH ROW EXECUTE FUNCTION update_user_memory_queries();

-- ============================================
-- INITIAL DATA & PERMISSIONS
-- ============================================

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO raguser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO raguser;

-- Insert test user (password: testpass123)
-- Password hash is bcrypt of "testpass123"
INSERT INTO users (id, email, username, password_hash, full_name, is_active, is_verified)
VALUES (
    'test_user_001',
    'test@example.com',
    'testuser',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5K5YvGZcqK/TK',
    'Test User',
    true,
    true
) ON CONFLICT (id) DO NOTHING;

-- Initialize user memory for test user
INSERT INTO user_memory (id, user_id, learning_level, preferred_topics)
VALUES (
    'memory_test_001',
    'test_user_001',
    'intermediate',
    '["photosynthesis", "biology", "chemistry"]'::jsonb
) ON CONFLICT (user_id) DO NOTHING;

-- Display success message
DO $$
BEGIN
    RAISE NOTICE '================================================';
    RAISE NOTICE 'Database initialized successfully!';
    RAISE NOTICE '================================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  Authentication: users, user_sessions';
    RAISE NOTICE '  Short-term Memory: conversations, conversation_metadata';
    RAISE NOTICE '  Long-term Memory: user_memory, user_topic_interest, conversation_summaries';
    RAISE NOTICE '  Analytics: query_logs, user_feedback, system_metrics';
    RAISE NOTICE '';
    RAISE NOTICE 'pgvector extension: ENABLED';
    RAISE NOTICE 'Test user created: test@example.com / testpass123';
    RAISE NOTICE '================================================';
END $$;