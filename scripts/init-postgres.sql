-- ThreatRAG PostgreSQL 初始化脚本
-- 创建数据库和表结构

-- 确保在 knowledge_db 数据库中创建表
\c knowledge_db;

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建知识库数据库表
CREATE TABLE IF NOT EXISTS knowledge_databases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    db_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    creator_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}'
);

-- 创建文档表
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    db_id VARCHAR(255) NOT NULL,
    document_id VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    content TEXT,
    file_path TEXT,
    file_type VARCHAR(100),
    file_size BIGINT,
    chunk_count INTEGER DEFAULT 0,
    creator_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    FOREIGN KEY (db_id) REFERENCES knowledge_databases(db_id) ON DELETE CASCADE
);

-- 创建文档块表
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL,
    chunk_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    chunk_index INTEGER,
    token_count INTEGER,
    creator_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- 创建会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255),
    title VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

-- 创建消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL,
    message_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    creator_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    token_count INTEGER,
    metadata JSONB DEFAULT '{}',
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
);

-- 创建向量索引任务表
CREATE TABLE IF NOT EXISTS vector_index_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255) NOT NULL UNIQUE,
    db_id VARCHAR(255) NOT NULL,
    document_id UUID,
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    FOREIGN KEY (db_id) REFERENCES knowledge_databases(db_id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- 创建系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(255) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_knowledge_databases_db_id ON knowledge_databases(db_id);
CREATE INDEX IF NOT EXISTS idx_documents_db_id ON documents(db_id);
CREATE INDEX IF NOT EXISTS idx_documents_document_id ON documents(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_chunk_id ON document_chunks(chunk_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_session_id ON chat_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_vector_index_tasks_task_id ON vector_index_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_vector_index_tasks_db_id ON vector_index_tasks(db_id);
CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key);

-- 创建全文搜索索引
CREATE INDEX IF NOT EXISTS idx_documents_content_gin ON documents USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_document_chunks_content_gin ON document_chunks USING gin(to_tsvector('english', content));

-- 插入默认配置
INSERT INTO system_config (config_key, config_value, description) VALUES 
    ('system_version', '"1.0.0"', 'ThreatRAG系统版本'),
    ('default_embedding_model', '"BAAI/bge-m3"', '默认嵌入模型'),
    ('max_chunk_size', '1000', '最大文档块大小'),
    ('chunk_overlap', '200', '文档块重叠大小')
ON CONFLICT (config_key) DO NOTHING;

-- 更新时间戳触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要的表创建更新时间戳触发器
CREATE TRIGGER update_knowledge_databases_updated_at BEFORE UPDATE ON knowledge_databases FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_chat_sessions_updated_at BEFORE UPDATE ON chat_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_vector_index_tasks_updated_at BEFORE UPDATE ON vector_index_tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- 增量迁移：将 ORM 模型新增的列补入已有表
-- 如果表已存在（不含这些列），逐条 ALTER TABLE 补列
-- 如表是从头创建（CREATE TABLE IF NOT EXISTS），本段不产生任何影响
-- =============================================

-- knowledge_databases: 补 creator_id
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'knowledge_databases' AND column_name = 'creator_id') THEN
        ALTER TABLE knowledge_databases ADD COLUMN creator_id VARCHAR(255);
    END IF;
END $$;

-- documents: 补 creator_id
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'creator_id') THEN
        ALTER TABLE documents ADD COLUMN creator_id VARCHAR(255);
    END IF;
END $$;

-- document_chunks: 补 creator_id
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'document_chunks' AND column_name = 'creator_id') THEN
        ALTER TABLE document_chunks ADD COLUMN creator_id VARCHAR(255);
    END IF;
END $$;

-- chat_sessions: 补 user_id
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chat_sessions' AND column_name = 'user_id') THEN
        ALTER TABLE chat_sessions ADD COLUMN user_id VARCHAR(255);
    END IF;
END $$;

-- chat_messages: 补 creator_id
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chat_messages' AND column_name = 'creator_id') THEN
        ALTER TABLE chat_messages ADD COLUMN creator_id VARCHAR(255);
    END IF;
END $$;
