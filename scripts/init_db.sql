-- scripts/init_db.sql
-- Database initialization script for Educational RAG
-- This runs automatically when PostgreSQL container starts for the first time

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create conversations table for chat history
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(50) PRIMARY KEY,
    conversation_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    message TEXT NOT NULL,
    sources_used JSONB,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    embedding vector(1024)  -- Optional: for semantic search of chat history
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_conversations_conversation_id ON conversations(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp DESC);

-- Create table for query logs and metrics
CREATE TABLE IF NOT EXISTS query_logs (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
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

-- Create table for user feedback
CREATE TABLE IF NOT EXISTS user_feedback (
    id VARCHAR(50) PRIMARY KEY,
    query_log_id VARCHAR(50) REFERENCES query_logs(id),
    user_id VARCHAR(50) NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_type VARCHAR(20) CHECK (feedback_type IN ('helpful', 'not_helpful', 'incorrect', 'incomplete')),
    comment TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_query_log_id ON user_feedback(query_log_id);

-- Create table for system metrics
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO raguser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO raguser;

-- Insert initial test data (optional, for verification)
INSERT INTO conversations (id, conversation_id, user_id, role, message, sources_used, metadata, timestamp)
VALUES (
    'test_001',
    'conv_test_001',
    'test_user',
    'user',
    'Test message to verify database setup',
    '[]'::jsonb,
    '{"test": true}'::jsonb,
    CURRENT_TIMESTAMP
) ON CONFLICT (id) DO NOTHING;

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Database initialized successfully!';
    RAISE NOTICE 'Tables created: conversations, query_logs, user_feedback, system_metrics';
    RAISE NOTICE 'pgvector extension enabled';
END $$;