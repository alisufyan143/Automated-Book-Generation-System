"""
Outline Generator module for the Book Generation System.
Handles Stage 1: Input processing and outline generation with gating logic.
"""

from typing import Optional, List, Dict, Any
from database import Database
from llm_service import LLMService
from input_handler import InputHandler
from config import Config


class OutlineGenerator:
    """Handles outline generation workflow with gating logic."""
    
    def __init__(self):
        """Initialize outline generator with dependencies."""
        self.db = Database()
        self.llm = LLMService()
        self.input_handler = InputHandler()
    
    def process_input_file(self) -> Dict[str, Any]:
        """
        Process input Excel file and create book entries in database.
        
        Returns:
            Summary of processed books
        """
        print("\n📖 Reading books from input file...")
        books = self.input_handler.get_books_for_processing()
        
        results = {
            "created": [],
            "skipped": [],
            "errors": []
        }
        
        for book_data in books:
            try:
                # Check if book already exists
                existing = self._find_existing_book(book_data["title"])
                if existing:
                    print(f"⏭️  Skipping '{book_data['title']}' - already exists in database")
                    results["skipped"].append(book_data["title"])
                    continue
                
                # Create new book entry
                book = self.db.create_book(
                    title=book_data["title"],
                    notes_on_outline_before=book_data["notes_on_outline_before"]
                )
                print(f"✅ Created: '{book_data['title']}'")
                results["created"].append(book)
                
            except Exception as e:
                print(f"❌ Error creating '{book_data['title']}': {e}")
                results["errors"].append({"title": book_data["title"], "error": str(e)})
        
        return results
    
    def _find_existing_book(self, title: str) -> Optional[Dict[str, Any]]:
        """Check if a book with the same title exists."""
        all_books = self.db.get_all_books()
        for book in all_books:
            if book["title"].lower().strip() == title.lower().strip():
                return book
        return None
    
    def generate_outlines_for_pending(self) -> List[Dict[str, Any]]:
        """
        Generate outlines for all books that have pre-outline notes but no outline.
        
        Returns:
            List of books with newly generated outlines
        """
        print("\n📝 Checking for books pending outline generation...")
        
        all_books = self.db.get_all_books()
        processed = []
        
        for book in all_books:
            # Skip if already has outline
            if book.get("outline"):
                print(f"⏭️  '{book['title']}' - Already has outline")
                continue
            
            # Skip if no pre-outline notes (required per spec)
            if not book.get("notes_on_outline_before"):
                print(f"⏭️  '{book['title']}' - No pre-outline notes, skipping")
                continue
            
            # Generate outline
            print(f"\n🤖 Generating outline for: '{book['title']}'...")
            try:
                outline = self.llm.generate_outline(
                    title=book["title"],
                    notes=book["notes_on_outline_before"]
                )
                
                # Store outline and set status to 'yes' (waiting for review)
                self.db.update_book(
                    book["id"],
                    outline=outline,
                    status_outline_notes="yes"  # Waiting for editor review
                )
                
                print(f"✅ Outline generated ({len(outline)} chars)")
                processed.append({
                    "id": book["id"],
                    "title": book["title"],
                    "outline_length": len(outline)
                })
                
            except Exception as e:
                print(f"❌ Error generating outline: {e}")
                self.db.update_book(book["id"], book_output_status="error")
        
        return processed
    
    def check_outline_status(self, book_id: str) -> Dict[str, Any]:
        """
        Check outline status and proceed based on gating logic.
        
        Gating Logic:
        - 'yes' → Waiting for editor notes
        - 'no_notes_needed' → Can proceed to chapters
        - 'no' or empty → Paused
        
        Returns:
            Status dict with action to take
        """
        book = self.db.get_book(book_id)
        if not book:
            return {"error": "Book not found"}
        
        status = book.get("status_outline_notes", "pending")
        
        if status == "yes":
            # Check if there are post-outline notes
            if book.get("notes_on_outline_after"):
                return {
                    "status": status,
                    "action": "regenerate",
                    "message": "Post-outline notes found. Ready to regenerate outline.",
                    "book": book
                }
            return {
                "status": status,
                "action": "wait",
                "message": "Waiting for editor to review and add notes.",
                "book": book
            }
        
        elif status == "no_notes_needed":
            return {
                "status": status,
                "action": "proceed",
                "message": "Ready to proceed to chapter generation.",
                "book": book
            }
        
        else:  # 'no', empty, or 'pending'
            return {
                "status": status,
                "action": "pause",
                "message": f"Workflow paused. Status: {status}",
                "book": book
            }
    
    def regenerate_outline(self, book_id: str) -> Dict[str, Any]:
        """
        Regenerate outline based on post-outline notes.
        
        Returns:
            Updated book info
        """
        book = self.db.get_book(book_id)
        if not book:
            return {"error": "Book not found"}
        
        if not book.get("notes_on_outline_after"):
            return {"error": "No post-outline notes to use for regeneration"}
        
        if not book.get("outline"):
            return {"error": "No existing outline to regenerate"}
        
        print(f"\n🔄 Regenerating outline for: '{book['title']}'...")
        
        try:
            new_outline = self.llm.regenerate_outline(
                title=book["title"],
                original_outline=book["outline"],
                feedback=book["notes_on_outline_after"]
            )
            
            # Update outline and reset status
            self.db.update_book(
                book_id,
                outline=new_outline,
                notes_on_outline_after=None,  # Clear used notes
                status_outline_notes="yes"    # Back to waiting for review
            )
            
            print(f"✅ Outline regenerated ({len(new_outline)} chars)")
            return {
                "success": True,
                "book_id": book_id,
                "outline_length": len(new_outline)
            }
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"error": str(e)}
    
    def approve_outline(self, book_id: str, needs_notes: bool = False) -> Dict[str, Any]:
        """
        Approve outline and set status for next stage.
        
        Args:
            book_id: Book ID
            needs_notes: If True, set status to 'yes' to wait for more notes
                        If False, set status to 'no_notes_needed' to proceed
        """
        status = "yes" if needs_notes else "no_notes_needed"
        
        self.db.update_book(
            book_id,
            status_outline_notes=status,
            book_output_status="in_progress" if not needs_notes else "pending"
        )
        
        action = "waiting for notes" if needs_notes else "ready for chapter generation"
        print(f"✅ Outline status updated: {action}")
        
        return {"success": True, "status": status, "action": action}
    
    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Get all books waiting for outline review."""
        all_books = self.db.get_all_books()
        return [
            {
                "id": book["id"],
                "title": book["title"],
                "status": book.get("status_outline_notes"),
                "has_outline": bool(book.get("outline")),
                "has_post_notes": bool(book.get("notes_on_outline_after"))
            }
            for book in all_books
            if book.get("outline") and book.get("status_outline_notes") == "yes"
        ]
    
    def get_ready_for_chapters(self) -> List[Dict[str, Any]]:
        """Get all books ready for chapter generation."""
        all_books = self.db.get_all_books()
        return [
            book for book in all_books
            if book.get("status_outline_notes") == "no_notes_needed"
            and book.get("outline")
        ]


# ==========================================================================
# TEST
# ==========================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("OUTLINE GENERATOR TEST")
    print("=" * 60)
    
    generator = OutlineGenerator()
    
    # Step 1: Process input file
    print("\n" + "=" * 40)
    print("STEP 1: Process Input File")
    print("=" * 40)
    results = generator.process_input_file()
    print(f"\n📊 Results: {len(results['created'])} created, {len(results['skipped'])} skipped")
    
    # Step 2: Generate outlines for pending books
    print("\n" + "=" * 40)
    print("STEP 2: Generate Outlines")
    print("=" * 40)
    processed = generator.generate_outlines_for_pending()
    print(f"\n📊 Generated {len(processed)} outline(s)")
    
    # Step 3: Show pending reviews
    print("\n" + "=" * 40)
    print("STEP 3: Books Waiting for Review")
    print("=" * 40)
    pending = generator.get_pending_reviews()
    for book in pending:
        print(f"   📚 {book['title']} (ID: {book['id'][:8]}...)")
    
    if not pending:
        print("   No books waiting for review")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
