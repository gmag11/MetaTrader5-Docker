-- Initial schema for copytrader database
-- This migration creates the core tables for position mapping and operation tracking

-- Position mappings: tracks master ticket to slave tickets
CREATE TABLE IF NOT EXISTS position_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    master_ticket INTEGER NOT NULL,
    slave_name TEXT NOT NULL,
    slave_ticket INTEGER NOT NULL,
    master_volume REAL NOT NULL,
    slave_volume REAL NOT NULL,
    symbol TEXT NOT NULL,
    direction INTEGER NOT NULL,  -- 0=BUY, 1=SELL
    status TEXT DEFAULT 'open',  -- open, closed, error
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    UNIQUE(master_ticket, slave_name)
);

-- Operation queue for retries
CREATE TABLE IF NOT EXISTS operation_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type TEXT NOT NULL,  -- open, close, modify, partial_close
    master_ticket INTEGER NOT NULL,
    slave_name TEXT NOT NULL,
    payload TEXT NOT NULL,  -- JSON with operation details
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    next_retry_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Audit log for tracking all events
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,  -- position_opened, position_closed, etc.
    master_ticket INTEGER,
    slave_name TEXT,
    slave_ticket INTEGER,
    details TEXT,  -- JSON with additional details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_mappings_master ON position_mappings(master_ticket);
CREATE INDEX IF NOT EXISTS idx_mappings_status ON position_mappings(status);
CREATE INDEX IF NOT EXISTS idx_mappings_slave ON position_mappings(slave_name);
CREATE INDEX IF NOT EXISTS idx_queue_status ON operation_queue(status, next_retry_at);
CREATE INDEX IF NOT EXISTS idx_queue_slave ON operation_queue(slave_name);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_master ON audit_log(master_ticket);
