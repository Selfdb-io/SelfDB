-- SelfDB Initial Schema Migration
-- Creates the core application tables for SelfDB BaaS platform

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core Application Tables

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(20) NOT NULL DEFAULT 'USER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ
);

-- Buckets table
CREATE TABLE IF NOT EXISTS buckets (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    owner_id VARCHAR(36) NOT NULL REFERENCES users(id),
    public BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Files table
CREATE TABLE IF NOT EXISTS files (
    id VARCHAR(36) PRIMARY KEY,
    bucket_id VARCHAR(36) NOT NULL REFERENCES buckets(id),
    name VARCHAR(500) NOT NULL,
    owner_id VARCHAR(36) REFERENCES users(id),
    size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    metadata JSONB,
    checksum_md5 VARCHAR(32),
    checksum_sha256 VARCHAR(64),
    version INTEGER NOT NULL DEFAULT 1,
    is_latest BOOLEAN NOT NULL DEFAULT TRUE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Functions table (Enhanced for Event-Driven System)
CREATE TABLE IF NOT EXISTS functions (
    id VARCHAR(36) PRIMARY KEY,
    
    -- Basic Metadata
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    code TEXT NOT NULL,
    runtime VARCHAR(50) NOT NULL DEFAULT 'deno',
    owner_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Function Status & Control
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    deployment_status VARCHAR(20) DEFAULT 'pending',
    deployment_error TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Execution Configuration
    timeout_seconds INTEGER NOT NULL DEFAULT 30,
    memory_limit_mb INTEGER NOT NULL DEFAULT 512,
    max_concurrent INTEGER NOT NULL DEFAULT 10,
    
    -- Environment Variables (Encrypted at rest)
    env_vars JSONB DEFAULT '{}',
    env_vars_updated_at TIMESTAMPTZ,
    
    -- Execution Metrics (Cached aggregate data)
    execution_count INTEGER NOT NULL DEFAULT 0,
    execution_success_count INTEGER NOT NULL DEFAULT 0,
    execution_error_count INTEGER NOT NULL DEFAULT 0,
    last_executed_at TIMESTAMPTZ,
    avg_execution_time_ms INTEGER,
    
    -- Timestamps
    last_deployed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT timeout_range CHECK (timeout_seconds >= 5 AND timeout_seconds <= 300),
    CONSTRAINT memory_range CHECK (memory_limit_mb >= 128 AND memory_limit_mb <= 4096),
    CONSTRAINT max_concurrent_range CHECK (max_concurrent >= 1 AND max_concurrent <= 100)
);

-- Tables table (for custom table management)
CREATE TABLE IF NOT EXISTS tables (
    name VARCHAR(255) PRIMARY KEY,
    schema JSONB NOT NULL,
    public BOOLEAN NOT NULL DEFAULT FALSE,
    owner_id VARCHAR(36) NOT NULL REFERENCES users(id),
    description TEXT,
    metadata JSONB,
    row_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Data Records table (generic JSON storage)
CREATE TABLE IF NOT EXISTS data_records (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
