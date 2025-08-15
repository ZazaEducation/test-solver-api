-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Create enum types
CREATE TYPE test_status AS ENUM ('processing', 'completed', 'failed');
CREATE TYPE question_type AS ENUM ('multiple_choice', 'short_answer', 'essay', 'true_false', 'fill_blank', 'other');

-- Tests table
CREATE TABLE tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL,
    title TEXT NOT NULL,
    file_url TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    status test_status NOT NULL DEFAULT 'processing',
    processing_time NUMERIC,
    total_questions INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Questions table
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    question_type question_type NOT NULL,
    options TEXT[] DEFAULT '{}',
    ai_answer TEXT,
    confidence DECIMAL(3,2) CHECK (confidence >= 0 AND confidence <= 1),
    explanation TEXT,
    processing_time NUMERIC,
    created_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_test_question UNIQUE (test_id, question_number)
);

-- Knowledge base for RAG
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_url TEXT,
    category TEXT,
    embedding vector(384), -- Sentence transformer dimension
    created_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_date TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Processing jobs table for async processing
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_date TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_tests_created_by ON tests(created_by);
CREATE INDEX idx_tests_status ON tests(status);
CREATE INDEX idx_tests_created_date ON tests(created_date);

CREATE INDEX idx_questions_test_id ON questions(test_id);
CREATE INDEX idx_questions_number ON questions(question_number);
CREATE INDEX idx_questions_type ON questions(question_type);

CREATE INDEX idx_knowledge_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_knowledge_category ON knowledge_base(category);

CREATE INDEX idx_processing_jobs_test_id ON processing_jobs(test_id);
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);

-- Update triggers for updated_date
CREATE OR REPLACE FUNCTION update_updated_date_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_date = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tests_updated_date BEFORE UPDATE ON tests
    FOR EACH ROW EXECUTE FUNCTION update_updated_date_column();

CREATE TRIGGER update_questions_updated_date BEFORE UPDATE ON questions
    FOR EACH ROW EXECUTE FUNCTION update_updated_date_column();

CREATE TRIGGER update_knowledge_base_updated_date BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_date_column();

-- RLS (Row Level Security) policies
ALTER TABLE tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_jobs ENABLE ROW LEVEL SECURITY;

-- Basic policies (can be extended based on auth requirements)
CREATE POLICY "Users can view their own tests" ON tests
    FOR SELECT USING (auth.email() = created_by);

CREATE POLICY "Users can create tests" ON tests
    FOR INSERT WITH CHECK (auth.email() = created_by);

CREATE POLICY "Users can update their own tests" ON tests
    FOR UPDATE USING (auth.email() = created_by);

-- Questions inherit access from tests
CREATE POLICY "Users can view questions from their tests" ON questions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM tests 
            WHERE tests.id = questions.test_id 
            AND tests.created_by = auth.email()
        )
    );

CREATE POLICY "Service can manage all questions" ON questions
    FOR ALL USING (current_setting('role') = 'service_role');

-- Processing jobs policies
CREATE POLICY "Users can view their processing jobs" ON processing_jobs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM tests 
            WHERE tests.id = processing_jobs.test_id 
            AND tests.created_by = auth.email()
        )
    );

-- Functions for vector similarity search
CREATE OR REPLACE FUNCTION search_knowledge_base(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    title text,
    content text,
    source_url text,
    category text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        kb.id,
        kb.title,
        kb.content,
        kb.source_url,
        kb.category,
        1 - (kb.embedding <=> query_embedding) AS similarity
    FROM knowledge_base kb
    WHERE 1 - (kb.embedding <=> query_embedding) > match_threshold
    ORDER BY kb.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;