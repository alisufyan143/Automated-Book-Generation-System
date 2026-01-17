"""
Chapter Generator module for the Book Generation System.
Handles Stage 2: Chapter generation with context chaining and gating logic.
"""

import re
from typing import Optional, List, Dict, Any
from database import Database
from llm_service import LLMService
from config import Config


class ChapterGenerator:
    """Handles chapter generation workflow with context chaining."""
    
    def __init__(self):
        """Initialize chapter generator with dependencies."""
        self.db = Database()
        self.llm = LLMService()
    
    # ==========================================================================
    # OUTLINE PARSING
    # ==========================================================================
    
    def parse_outline_to_chapters(self, outline: str) -> List[Dict[str, Any]]:
        """
        Parse the outline text to extract chapter titles and descriptions.
        
        Args:
            outline: The generated outline in markdown format
            
        Returns:
            List of dicts with chapter_number, title, description
        """
        chapters = []
        
        # Pattern to match chapter headings like "## Chapter 1:", "## Chapter 2:", etc.
        # Also matches patterns like "## 1.", "### Chapter 1 -", etc.
        patterns = [
            r'##\s*Chapter\s*(\d+)[:\s-]*(.+?)(?=\n|$)',  # ## Chapter 1: Title
            r'###\s*Chapter\s*(\d+)[:\s-]*(.+?)(?=\n|$)',  # ### Chapter 1: Title
            r'##\s*(\d+)\.\s*(.+?)(?=\n|$)',               # ## 1. Title
            r'\*\*Chapter\s*(\d+)[:\s-]*(.+?)\*\*',        # **Chapter 1: Title**
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, outline, re.IGNORECASE | re.MULTILINE)
            if matches:
                for match in matches:
                    chapter_num = int(match[0])
                    title = match[1].strip().rstrip('*').strip()
                    
                    # Avoid duplicates
                    if not any(c['chapter_number'] == chapter_num for c in chapters):
                        chapters.append({
                            'chapter_number': chapter_num,
                            'title': title,
                            'description': ''  # Could extract from following text
                        })
                break
        
        # Sort by chapter number
        chapters.sort(key=lambda x: x['chapter_number'])
        
        # If no chapters found, try a more generic approach
        if not chapters:
            # Look for any numbered headings
            generic_pattern = r'(?:##|###)\s*(.+?)(?:\n|$)'
            matches = re.findall(generic_pattern, outline)
            
            for i, title in enumerate(matches[:10], 1):  # Max 10 chapters
                title = title.strip().rstrip(':').strip()
                if title and len(title) > 3:  # Skip very short matches
                    chapters.append({
                        'chapter_number': i,
                        'title': title,
                        'description': ''
                    })
        
        return chapters
    
    # ==========================================================================
    # CHAPTER CREATION IN DATABASE
    # ==========================================================================
    
    def initialize_chapters_for_book(self, book_id: str) -> List[Dict[str, Any]]:
        """
        Parse outline and create chapter entries in database.
        
        Args:
            book_id: The book ID
            
        Returns:
            List of created chapter records
        """
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")
        
        if not book.get("outline"):
            raise ValueError("Book has no outline to parse")
        
        # Check if chapters already exist
        existing_chapters = self.db.get_book_chapters(book_id)
        if existing_chapters:
            print(f"⚠️  Book already has {len(existing_chapters)} chapters")
            return existing_chapters
        
        # Parse outline
        parsed = self.parse_outline_to_chapters(book["outline"])
        print(f"📚 Parsed {len(parsed)} chapters from outline")
        
        # Create chapter entries
        created = []
        for ch in parsed:
            chapter = self.db.create_chapter(
                book_id=book_id,
                chapter_number=ch['chapter_number'],
                title=ch['title']
            )
            created.append(chapter)
            print(f"   ✅ Created: Chapter {ch['chapter_number']}: {ch['title']}")
        
        return created
    
    # ==========================================================================
    # CONTEXT CHAINING
    # ==========================================================================
    
    def get_context_for_chapter(self, book_id: str, chapter_number: int) -> str:
        """
        Build context from summaries of all previous chapters.
        
        Args:
            book_id: The book ID
            chapter_number: Current chapter number (will get summaries of 1 to N-1)
            
        Returns:
            Formatted context string
        """
        if chapter_number <= 1:
            return ""
        
        summaries = self.db.get_chapter_summaries(book_id, chapter_number - 1)
        
        if not summaries:
            return ""
        
        context_parts = []
        for s in summaries:
            if s.get('summary'):
                context_parts.append(
                    f"Chapter {s['chapter_number']}: {s.get('title', 'Untitled')}\n"
                    f"{s['summary']}"
                )
        
        return "\n\n".join(context_parts)
    
    # ==========================================================================
    # CHAPTER GENERATION
    # ==========================================================================
    
    def generate_chapter(self, book_id: str, chapter_number: int) -> Dict[str, Any]:
        """
        Generate a single chapter with context from previous chapters.
        
        Args:
            book_id: The book ID
            chapter_number: Chapter number to generate
            
        Returns:
            Updated chapter record
        """
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")
        
        # Get chapter record
        chapters = self.db.get_book_chapters(book_id)
        chapter = next((c for c in chapters if c['chapter_number'] == chapter_number), None)
        
        if not chapter:
            raise ValueError(f"Chapter {chapter_number} not found for this book")
        
        # Check if already generated
        if chapter.get('content'):
            print(f"⚠️  Chapter {chapter_number} already has content")
            return chapter
        
        # Get context from previous chapters
        context = self.get_context_for_chapter(book_id, chapter_number)
        previous_summaries = []
        
        if context:
            # Parse context into list format for LLM
            summaries = self.db.get_chapter_summaries(book_id, chapter_number - 1)
            previous_summaries = [
                {
                    'chapter_number': s['chapter_number'],
                    'title': s.get('title', ''),
                    'summary': s.get('summary', '')
                }
                for s in summaries
            ]
        
        print(f"\n🤖 Generating Chapter {chapter_number}: {chapter.get('title', 'Untitled')}...")
        if previous_summaries:
            print(f"   📚 Using context from {len(previous_summaries)} previous chapter(s)")
        
        # Update status to generating
        self.db.update_chapter(chapter['id'], status="generating")
        
        try:
            # Generate chapter content
            result = self.llm.generate_chapter(
                title=book['title'],
                outline=book['outline'],
                chapter_number=chapter_number,
                chapter_title=chapter.get('title', f'Chapter {chapter_number}'),
                previous_summaries=previous_summaries,
                chapter_notes=chapter.get('notes')
            )
            
            # Store content and summary
            updated = self.db.update_chapter_content(
                chapter_id=chapter['id'],
                content=result['content'],
                summary=result['summary'],
                status="generated"
            )
            
            # Set notes_status to 'yes' - waiting for review
            self.db.update_chapter(chapter['id'], notes_status="yes")
            
            print(f"✅ Chapter {chapter_number} generated ({len(result['content'])} chars)")
            print(f"   📝 Summary: {result['summary'][:100]}...")
            
            return updated
            
        except Exception as e:
            self.db.update_chapter(chapter['id'], status="error")
            raise e
    
    def generate_all_chapters(self, book_id: str, auto_approve: bool = False) -> List[Dict[str, Any]]:
        """
        Generate all chapters for a book sequentially.
        
        Args:
            book_id: The book ID
            auto_approve: If True, automatically approve chapters without waiting
            
        Returns:
            List of generated chapter records
        """
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")
        
        # Check if book is ready for chapters
        if book.get('status_outline_notes') != 'no_notes_needed':
            raise ValueError(
                f"Book outline not approved. Status: {book.get('status_outline_notes')}\n"
                "Set status_outline_notes to 'no_notes_needed' to proceed."
            )
        
        chapters = self.db.get_book_chapters(book_id)
        if not chapters:
            print("📚 No chapters found. Initializing from outline...")
            chapters = self.initialize_chapters_for_book(book_id)
        
        generated = []
        for chapter in chapters:
            # Check gating status
            status = self.check_chapter_status(chapter['id'])
            
            if status['action'] == 'skip':
                print(f"⏭️  Skipping Chapter {chapter['chapter_number']} - already completed")
                continue
            
            if status['action'] == 'wait' and not auto_approve:
                print(f"⏸️  Pausing at Chapter {chapter['chapter_number']} - waiting for notes")
                break
            
            # Generate chapter
            result = self.generate_chapter(book_id, chapter['chapter_number'])
            generated.append(result)
            
            # If auto_approve, mark as approved immediately
            if auto_approve:
                self.approve_chapter(chapter['id'])
        
        return generated
    
    # ==========================================================================
    # GATING LOGIC
    # ==========================================================================
    
    def check_chapter_status(self, chapter_id: str) -> Dict[str, Any]:
        """
        Check chapter status and determine action.
        
        Gating Logic:
        - 'yes' → Waiting for editor notes
        - 'no_notes_needed' → Can proceed/is approved
        - 'no' or empty → Paused
        
        Returns:
            Status dict with action
        """
        chapter = self.db.get_chapter(chapter_id)
        if not chapter:
            return {"error": "Chapter not found"}
        
        notes_status = chapter.get('notes_status', 'pending')
        content_status = chapter.get('status', 'pending')
        
        # Already approved
        if notes_status == 'no_notes_needed' or content_status == 'approved':
            return {
                "status": notes_status,
                "action": "skip",
                "message": "Chapter already approved",
                "chapter": chapter
            }
        
        # Has content and notes provided - ready to regenerate
        if chapter.get('content') and chapter.get('notes') and notes_status == 'yes':
            return {
                "status": notes_status,
                "action": "regenerate",
                "message": "Notes provided. Ready to regenerate.",
                "chapter": chapter
            }
        
        # Has content, waiting for notes
        if chapter.get('content') and notes_status == 'yes':
            return {
                "status": notes_status,
                "action": "wait",
                "message": "Waiting for editor review/notes",
                "chapter": chapter
            }
        
        # No content yet - needs generation
        if not chapter.get('content'):
            return {
                "status": content_status,
                "action": "generate",
                "message": "Ready for generation",
                "chapter": chapter
            }
        
        # Default: paused
        return {
            "status": notes_status,
            "action": "pause",
            "message": f"Paused. Status: {notes_status}",
            "chapter": chapter
        }
    
    def approve_chapter(self, chapter_id: str) -> Dict[str, Any]:
        """Approve a chapter to proceed."""
        self.db.update_chapter(
            chapter_id,
            notes_status="no_notes_needed",
            status="approved"
        )
        return {"success": True, "message": "Chapter approved"}
    
    def regenerate_chapter(self, chapter_id: str) -> Dict[str, Any]:
        """Regenerate a chapter based on editor notes."""
        chapter = self.db.get_chapter(chapter_id)
        if not chapter:
            return {"error": "Chapter not found"}
        
        if not chapter.get('notes'):
            return {"error": "No notes provided for regeneration"}
        
        book = self.db.get_book(chapter['book_id'])
        
        print(f"\n🔄 Regenerating Chapter {chapter['chapter_number']}...")
        
        result = self.llm.regenerate_chapter(
            title=book['title'],
            chapter_number=chapter['chapter_number'],
            chapter_title=chapter.get('title', ''),
            original_content=chapter['content'],
            feedback=chapter['notes']
        )
        
        # Update chapter
        self.db.update_chapter(
            chapter_id,
            content=result['content'],
            summary=result['summary'],
            notes=None,  # Clear used notes
            notes_status="yes",  # Back to waiting for review
            status="generated"
        )
        
        print(f"✅ Chapter regenerated ({len(result['content'])} chars)")
        return {"success": True, "content_length": len(result['content'])}
    
    # ==========================================================================
    # STATUS METHODS
    # ==========================================================================
    
    def get_book_progress(self, book_id: str) -> Dict[str, Any]:
        """Get chapter generation progress for a book."""
        book = self.db.get_book(book_id)
        if not book:
            return {"error": "Book not found"}
        
        chapters = self.db.get_book_chapters(book_id)
        
        return {
            "book_id": book_id,
            "title": book['title'],
            "total_chapters": len(chapters),
            "generated": len([c for c in chapters if c.get('content')]),
            "approved": len([c for c in chapters if c.get('status') == 'approved']),
            "pending": len([c for c in chapters if not c.get('content')]),
            "waiting_review": len([c for c in chapters if c.get('notes_status') == 'yes']),
            "chapters": [
                {
                    "number": c['chapter_number'],
                    "title": c.get('title', ''),
                    "status": c.get('status'),
                    "notes_status": c.get('notes_status'),
                    "has_content": bool(c.get('content')),
                    "has_summary": bool(c.get('summary'))
                }
                for c in chapters
            ]
        }


# ==========================================================================
# TEST
# ==========================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("CHAPTER GENERATOR TEST")
    print("=" * 70)
    
    generator = ChapterGenerator()
    
    # Get books ready for chapter generation
    from outline_generator import OutlineGenerator
    og = OutlineGenerator()
    
    ready_books = og.get_ready_for_chapters()
    
    if not ready_books:
        print("\n⚠️  No books ready for chapter generation!")
        print("   Books need status_outline_notes = 'no_notes_needed'")
        print("\n📚 Current books in database:")
        
        all_books = generator.db.get_all_books()
        for book in all_books:
            print(f"   - {book['title']}")
            print(f"     Status: {book.get('status_outline_notes')}")
            print(f"     ID: {book['id']}")
        
        if all_books:
            print("\n💡 To test chapter generation, run:")
            print(f"   python -c \"from database import Database; db = Database(); db.update_book('{all_books[0]['id']}', status_outline_notes='no_notes_needed')\"")
    else:
        # Test with first ready book
        book = ready_books[0]
        print(f"\n📚 Testing with: {book['title']}")
        print(f"   Book ID: {book['id']}")
        
        # Initialize chapters
        print("\n" + "=" * 40)
        print("STEP 1: Initialize Chapters from Outline")
        print("=" * 40)
        chapters = generator.initialize_chapters_for_book(book['id'])
        
        # Generate first chapter only (for testing)
        print("\n" + "=" * 40)
        print("STEP 2: Generate First Chapter")
        print("=" * 40)
        if chapters:
            first_chapter = generator.generate_chapter(book['id'], 1)
            
            # Show progress
            print("\n" + "=" * 40)
            print("STEP 3: Progress Report")
            print("=" * 40)
            progress = generator.get_book_progress(book['id'])
            print(f"\n📊 Progress for '{progress['title']}':")
            print(f"   Total: {progress['total_chapters']} chapters")
            print(f"   Generated: {progress['generated']}")
            print(f"   Approved: {progress['approved']}")
            print(f"   Pending: {progress['pending']}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
