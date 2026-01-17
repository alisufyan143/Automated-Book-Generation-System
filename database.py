"""
Database module for the Book Generation System.
Handles all Supabase database operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from config import Config


class Database:
    """Supabase database client and operations."""
    
    def __init__(self):
        """Initialize Supabase client."""
        if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
            raise ValueError("Supabase URL and Key must be set in .env file")
        
        self.client: Client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_KEY
        )
    
    # ==========================================================================
    # BOOK OPERATIONS
    # ==========================================================================
    
    def create_book(self, title: str, notes_on_outline_before: str = None) -> Dict[str, Any]:
        """Create a new book entry."""
        data = {
            "title": title,
            "notes_on_outline_before": notes_on_outline_before,
            "status_outline_notes": "pending",
            "book_output_status": "pending"
        }
        result = self.client.table("books").insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_book(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Get a book by ID."""
        result = self.client.table("books").select("*").eq("id", book_id).execute()
        return result.data[0] if result.data else None
    
    def get_all_books(self) -> List[Dict[str, Any]]:
        """Get all books."""
        result = self.client.table("books").select("*").order("created_at", desc=True).execute()
        return result.data or []
    
    def get_books_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get books by output status."""
        result = self.client.table("books").select("*").eq("book_output_status", status).execute()
        return result.data or []
    
    def update_book(self, book_id: str, **kwargs) -> Dict[str, Any]:
        """Update a book's fields."""
        result = self.client.table("books").update(kwargs).eq("id", book_id).execute()
        return result.data[0] if result.data else None
    
    def update_outline(self, book_id: str, outline: str, status: str = "yes") -> Dict[str, Any]:
        """Update book outline and set status."""
        return self.update_book(
            book_id, 
            outline=outline, 
            status_outline_notes=status
        )
    
    def delete_book(self, book_id: str) -> bool:
        """Delete a book and all its chapters (cascade)."""
        result = self.client.table("books").delete().eq("id", book_id).execute()
        return len(result.data) > 0 if result.data else False
    
    # ==========================================================================
    # CHAPTER OPERATIONS
    # ==========================================================================
    
    def create_chapter(
        self, 
        book_id: str, 
        chapter_number: int, 
        title: str = None
    ) -> Dict[str, Any]:
        """Create a new chapter entry."""
        data = {
            "book_id": book_id,
            "chapter_number": chapter_number,
            "title": title,
            "status": "pending",
            "notes_status": "pending"
        }
        result = self.client.table("chapters").insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_chapter(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        """Get a chapter by ID."""
        result = self.client.table("chapters").select("*").eq("id", chapter_id).execute()
        return result.data[0] if result.data else None
    
    def get_book_chapters(self, book_id: str) -> List[Dict[str, Any]]:
        """Get all chapters for a book, ordered by chapter number."""
        result = (
            self.client.table("chapters")
            .select("*")
            .eq("book_id", book_id)
            .order("chapter_number")
            .execute()
        )
        return result.data or []
    
    def get_chapter_summaries(self, book_id: str, up_to_chapter: int) -> List[Dict[str, Any]]:
        """Get summaries of chapters 1 to N for context chaining."""
        result = (
            self.client.table("chapters")
            .select("chapter_number, title, summary")
            .eq("book_id", book_id)
            .lt("chapter_number", up_to_chapter + 1)
            .order("chapter_number")
            .execute()
        )
        return result.data or []
    
    def update_chapter(self, chapter_id: str, **kwargs) -> Dict[str, Any]:
        """Update a chapter's fields."""
        result = self.client.table("chapters").update(kwargs).eq("id", chapter_id).execute()
        return result.data[0] if result.data else None
    
    def update_chapter_content(
        self, 
        chapter_id: str, 
        content: str, 
        summary: str,
        status: str = "generated"
    ) -> Dict[str, Any]:
        """Update chapter content and summary after generation."""
        return self.update_chapter(
            chapter_id,
            content=content,
            summary=summary,
            status=status
        )
    
    # ==========================================================================
    # NOTIFICATION OPERATIONS
    # ==========================================================================
    
    def log_notification(
        self, 
        book_id: str, 
        event_type: str, 
        message: str,
        recipient: str = None,
        status: str = "sent"
    ) -> Dict[str, Any]:
        """Log a notification event."""
        data = {
            "book_id": book_id,
            "event_type": event_type,
            "message": message,
            "recipient": recipient,
            "status": status
        }
        result = self.client.table("notifications_log").insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_book_notifications(self, book_id: str) -> List[Dict[str, Any]]:
        """Get all notifications for a book."""
        result = (
            self.client.table("notifications_log")
            .select("*")
            .eq("book_id", book_id)
            .order("sent_at", desc=True)
            .execute()
        )
        return result.data or []
    
    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================
    
    def test_connection(self) -> bool:
        """Test database connection by querying books table."""
        try:
            result = self.client.table("books").select("id").limit(1).execute()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def get_workflow_status(self, book_id: str) -> Dict[str, Any]:
        """Get complete workflow status for a book."""
        book = self.get_book(book_id)
        if not book:
            return None
        
        chapters = self.get_book_chapters(book_id)
        
        return {
            "book": book,
            "chapters": chapters,
            "total_chapters": len(chapters),
            "completed_chapters": len([c for c in chapters if c["status"] == "approved"]),
            "pending_chapters": len([c for c in chapters if c["status"] == "pending"]),
        }


# ==========================================================================
# TEST CONNECTION
# ==========================================================================
if __name__ == "__main__":
    print("Testing Supabase connection...")
    
    try:
        db = Database()
        
        if db.test_connection():
            print("✅ Successfully connected to Supabase!")
            
            # Show existing books
            books = db.get_all_books()
            print(f"\n📚 Found {len(books)} book(s) in database:")
            for book in books[:5]:  # Show max 5
                print(f"   - {book['title']} (Status: {book['book_output_status']})")
        else:
            print("❌ Connection test failed")
            
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
