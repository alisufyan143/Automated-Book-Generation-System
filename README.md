# 📚 Automated Book Generation System

A modular, scalable book generation system that accepts a title, generates an outline, writes chapters with feedback-based gating logic, and compiles the final draft.

## ⚙️ Tech Stack

| Component | Tool |
|-----------|------|
| Automation Engine | Python Scripts |
| Database | Supabase (PostgreSQL) |
| AI Model | Google Gemini (gemini-3-flash-preview) |
| Input Source | Local Excel (.xlsx) |
| Notifications | Email (SMTP) + MS Teams Webhooks |
| Output Files | .docx, .pdf, .txt |

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone/navigate to project
cd book-generator

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-key
GEMINI_API_KEY=your-gemini-api-key

# Optional - For notifications
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
NOTIFICATION_EMAIL=recipient@example.com
```

### 3. Setup Database

Run the SQL in `schema.sql` in your Supabase SQL Editor to create the required tables.

### 4. Prepare Input

Edit `input/books_input.xlsx` with your book titles and notes:

| title | notes_on_outline_before |
|-------|------------------------|
| My Book Title | Notes for the AI to use when generating the outline... |

### 5. Run the System

```bash
# Process input and generate outlines
python main.py process

# Check status
python main.py status

# Generate chapters for a specific book
python main.py chapters <book-id> --auto-approve

# Compile final book
python main.py compile <book-id> --force

# Or run complete pipeline
python main.py run --auto-approve
```

## 📁 Project Structure

```
book-generator/
├── config.py           # Configuration & environment variables
├── database.py         # Supabase database operations
├── llm_service.py      # Gemini API integration
├── input_handler.py    # Excel input processing
├── outline_generator.py # Stage 1: Outline generation
├── chapter_generator.py # Stage 2: Chapter generation with context
├── compiler.py         # Stage 3: Final compilation
├── notifications.py    # Email & Teams notifications
├── main.py             # CLI orchestrator
├── schema.sql          # Database schema
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── input/              # Input Excel files
└── output/             # Generated book files
```

## 🔄 Workflow Stages

### Stage 1: Input + Outline
1. Read books from Excel
2. Generate outline using Gemini
3. Store in database with status `yes` (waiting for review)
4. **Gating Logic**:
   - `yes`: Wait for editor notes
   - `no_notes_needed`: Proceed to chapters
   - `no/empty`: Pause

### Stage 2: Chapter Generation
1. Parse outline into chapters
2. Generate each chapter sequentially
3. Use previous chapter summaries as context
4. Store chapter + summary in database
5. **Per-chapter gating** for review

### Stage 3: Final Compilation
1. Check all chapters are approved
2. Compile to .docx, .pdf, .txt
3. Store output paths in database
4. Send completion notification

## 🛠️ CLI Commands

```bash
python main.py process          # Process Excel input
python main.py outlines         # Generate pending outlines
python main.py chapters <id>    # Generate chapters for a book
python main.py compile <id>     # Compile book to files
python main.py run              # Run full pipeline
python main.py status           # Show all books status
python main.py details <id>     # Show book details
python main.py approve outline <id>   # Approve outline
python main.py approve chapter <id>   # Approve chapter
```

## 📊 Database Schema

### Tables
- **books**: Book info, outline, status
- **chapters**: Individual chapters with summaries
- **notifications_log**: Notification history

### Key Fields
- `status_outline_notes`: yes/no/no_notes_needed
- `notes_status` (per chapter): yes/no/no_notes_needed
- `book_output_status`: pending/in_progress/completed

## 🔔 Notifications

Notifications are sent via email (SMTP) for:
- Outline ready for review
- Chapter waiting for notes
- Final draft compiled
- Errors/pauses

Configure in `.env` with Gmail app password or other SMTP credentials.

## 📝 License

MIT License - Built for assessment purposes.
