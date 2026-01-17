-- ============================================================================
-- BOOK GENERATION SYSTEM - DATABASE SCHEMA
-- Run this SQL in Supabase SQL Editor
-- ============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE: books
-- Main table storing book information, outlines, and status
-- ============================================================================
CREATE TABLE IF NOT EXISTS books (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Basic Info
    title TEXT NOT NULL,
    
    -- Outline Stage
    notes_on_outline_before TEXT,           -- Pre-outline notes from editor
    outline TEXT,                            -- Generated outline (JSON or markdown)
    notes_on_outline_after TEXT,            -- Post-outline feedback
    status_outline_notes TEXT DEFAULT 'pending' 
        CHECK (status_outline_notes IN ('pending', 'yes', 'no', 'no_notes_needed')),
    
    -- Final Stage
    final_review_notes TEXT,                -- Final review notes
    final_review_notes_status TEXT DEFAULT 'pending'
        CHECK (final_review_notes_status IN ('pending', 'yes', 'no', 'no_notes_needed')),
    book_output_status TEXT DEFAULT 'pending'
        CHECK (book_output_status IN ('pending', 'in_progress', 'completed', 'paused', 'error')),
    
    -- Output paths
    output_docx_path TEXT,
    output_pdf_path TEXT,
    output_txt_path TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- TABLE: chapters
-- Individual chapters for each book with summaries for context chaining
-- ============================================================================
CREATE TABLE IF NOT EXISTS chapters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    
    -- Chapter Info
    chapter_number INTEGER NOT NULL,
    title TEXT,
    content TEXT,                           -- Full chapter content
    summary TEXT,                           -- Summary for context chaining
    
    -- Review
    notes TEXT,                             -- Editor notes for this chapter
    notes_status TEXT DEFAULT 'pending'
        CHECK (notes_status IN ('pending', 'yes', 'no', 'no_notes_needed')),
    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending', 'generating', 'generated', 'reviewed', 'approved', 'error')),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique chapter numbers per book
    UNIQUE(book_id, chapter_number)
);

-- ============================================================================
-- TABLE: notifications_log
-- Track all notifications sent
-- ============================================================================
CREATE TABLE IF NOT EXISTS notifications_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    book_id UUID REFERENCES books(id) ON DELETE CASCADE,
    
    -- Notification details
    event_type TEXT NOT NULL
        CHECK (event_type IN (
            'outline_ready', 
            'waiting_chapter_notes', 
            'chapter_ready',
            'final_draft_ready', 
            'error_pause',
            'book_completed'
        )),
    message TEXT,
    recipient TEXT,                         -- Email or webhook URL
    status TEXT DEFAULT 'sent'
        CHECK (status IN ('sent', 'failed', 'pending')),
    
    -- Timestamps
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDEXES for better query performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_books_status ON books(book_output_status);
CREATE INDEX IF NOT EXISTS idx_chapters_book_id ON chapters(book_id);
CREATE INDEX IF NOT EXISTS idx_chapters_status ON chapters(status);
CREATE INDEX IF NOT EXISTS idx_notifications_book_id ON notifications_log(book_id);

-- ============================================================================
-- TRIGGER: Auto-update updated_at timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_books_updated_at 
    BEFORE UPDATE ON books 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chapters_updated_at 
    BEFORE UPDATE ON chapters 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Row Level Security (RLS) - Enable for production
-- For now, we'll use service role key which bypasses RLS
-- ============================================================================
-- ALTER TABLE books ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE chapters ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE notifications_log ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================
SELECT 'Database schema created successfully!' as status;
