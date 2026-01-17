"""
Main Orchestrator for the Book Generation System.
Provides CLI interface and coordinates all workflow stages.
"""

import argparse
import sys
from typing import Optional

from config import Config
from database import Database
from input_handler import InputHandler
from outline_generator import OutlineGenerator
from chapter_generator import ChapterGenerator
from compiler import BookCompiler
from notifications import NotificationService


class BookGenerationOrchestrator:
    """Main orchestrator that coordinates all workflow stages."""
    
    def __init__(self):
        """Initialize orchestrator with all components."""
        self.db = Database()
        self.outline_gen = OutlineGenerator()
        self.chapter_gen = ChapterGenerator()
        self.compiler = BookCompiler()
        self.notifier = NotificationService()
    
    # ==========================================================================
    # WORKFLOW COMMANDS
    # ==========================================================================
    
    def process_input(self):
        """Process input Excel file and create book entries."""
        print("\n" + "=" * 60)
        print("STAGE 1: PROCESSING INPUT FILE")
        print("=" * 60)
        
        results = self.outline_gen.process_input_file()
        
        print(f"\n📊 Summary:")
        print(f"   Created: {len(results['created'])} book(s)")
        print(f"   Skipped: {len(results['skipped'])} book(s)")
        
        if results['errors']:
            print(f"   Errors: {len(results['errors'])}")
        
        return results
    
    def generate_outlines(self):
        """Generate outlines for pending books."""
        print("\n" + "=" * 60)
        print("STAGE 1: GENERATING OUTLINES")
        print("=" * 60)
        
        processed = self.outline_gen.generate_outlines_for_pending()
        
        # Send notifications for each completed outline
        for book in processed:
            self.notifier.notify_outline_ready(book['id'])
        
        print(f"\n📊 Generated {len(processed)} outline(s)")
        return processed
    
    def generate_chapters(self, book_id: str, auto_approve: bool = False):
        """Generate chapters for a specific book."""
        book = self.db.get_book(book_id)
        if not book:
            print(f"❌ Book not found: {book_id}")
            return
        
        print("\n" + "=" * 60)
        print(f"STAGE 2: GENERATING CHAPTERS")
        print(f"Book: {book['title']}")
        print("=" * 60)
        
        try:
            generated = self.chapter_gen.generate_all_chapters(book_id, auto_approve)
            
            print(f"\n📊 Generated {len(generated)} chapter(s)")
            
            # Get progress
            progress = self.chapter_gen.get_book_progress(book_id)
            print(f"   Total: {progress['total_chapters']}")
            print(f"   Generated: {progress['generated']}")
            print(f"   Approved: {progress['approved']}")
            
            return generated
            
        except ValueError as e:
            print(f"❌ Error: {e}")
            return None
    
    def compile_book(self, book_id: str, formats: list = None, force: bool = False):
        """Compile book to output files."""
        book = self.db.get_book(book_id)
        if not book:
            print(f"❌ Book not found: {book_id}")
            return
        
        print("\n" + "=" * 60)
        print(f"STAGE 3: COMPILING BOOK")
        print(f"Book: {book['title']}")
        print("=" * 60)
        
        results = self.compiler.compile_book(book_id, formats, force)
        
        # Send notification
        if all(not str(v).startswith('Error') for v in results.values()):
            self.notifier.notify_final_draft_ready(book_id, results)
        
        return results
    
    def run_full_pipeline(self, book_id: str = None, auto_approve: bool = False):
        """
        Run the complete pipeline for a book.
        
        Args:
            book_id: Specific book ID, or None to process first available
            auto_approve: If True, auto-approve all stages
        """
        print("\n" + "=" * 70)
        print("RUNNING FULL BOOK GENERATION PIPELINE")
        print("=" * 70)
        
        # If no book_id, get first pending book
        if not book_id:
            books = self.db.get_all_books()
            book_id = books[0]['id'] if books else None
        
        if not book_id:
            print("❌ No books found. Process input file first.")
            return
        
        book = self.db.get_book(book_id)
        print(f"\n📚 Processing: {book['title']}")
        
        # Stage 1: Generate outline if needed
        if not book.get('outline'):
            print("\n📝 Generating outline...")
            self.outline_gen.generate_outlines_for_pending()
            book = self.db.get_book(book_id)  # Refresh
        
        if auto_approve and book.get('status_outline_notes') != 'no_notes_needed':
            print("✅ Auto-approving outline...")
            self.outline_gen.approve_outline(book_id, needs_notes=False)
        
        # Stage 2: Generate chapters
        print("\n📖 Generating chapters...")
        try:
            self.chapter_gen.generate_all_chapters(book_id, auto_approve=auto_approve)
        except ValueError as e:
            print(f"⚠️  {e}")
            return
        
        # Stage 3: Compile if all chapters approved
        progress = self.chapter_gen.get_book_progress(book_id)
        if progress['approved'] == progress['total_chapters']:
            print("\n📄 Compiling book...")
            self.compile_book(book_id, force=True)
            self.notifier.notify_book_completed(book_id)
        else:
            print(f"\n⏳ Chapters not fully approved: {progress['approved']}/{progress['total_chapters']}")
    
    # ==========================================================================
    # STATUS COMMANDS
    # ==========================================================================
    
    def show_status(self):
        """Show status of all books."""
        print("\n" + "=" * 70)
        print("BOOK GENERATION SYSTEM STATUS")
        print("=" * 70)
        
        books = self.db.get_all_books()
        
        if not books:
            print("\n📭 No books in the system.")
            print("   Run: python main.py process")
            return
        
        for book in books:
            print(f"\n📚 {book['title']}")
            print(f"   ID: {book['id']}")
            print(f"   Outline: {'✅ Generated' if book.get('outline') else '❌ Pending'}")
            print(f"   Outline Status: {book.get('status_outline_notes', 'N/A')}")
            print(f"   Book Status: {book.get('book_output_status', 'N/A')}")
            
            chapters = self.db.get_book_chapters(book['id'])
            if chapters:
                generated = len([c for c in chapters if c.get('content')])
                approved = len([c for c in chapters if c.get('status') == 'approved'])
                print(f"   Chapters: {generated}/{len(chapters)} generated, {approved} approved")
            
            # Output files
            if book.get('output_docx_path'):
                print(f"   📄 DOCX: {book['output_docx_path']}")
            if book.get('output_pdf_path'):
                print(f"   📄 PDF: {book['output_pdf_path']}")
            if book.get('output_txt_path'):
                print(f"   📄 TXT: {book['output_txt_path']}")
    
    def show_book_details(self, book_id: str):
        """Show detailed status for a specific book."""
        book = self.db.get_book(book_id)
        if not book:
            print(f"❌ Book not found: {book_id}")
            return
        
        print("\n" + "=" * 70)
        print(f"BOOK DETAILS: {book['title']}")
        print("=" * 70)
        
        print(f"\n📚 Basic Info:")
        print(f"   ID: {book['id']}")
        print(f"   Created: {book.get('created_at', 'N/A')}")
        
        print(f"\n📝 Outline Stage:")
        print(f"   Pre-notes: {'✅ Yes' if book.get('notes_on_outline_before') else '❌ No'}")
        print(f"   Outline: {'✅ Generated' if book.get('outline') else '❌ Pending'}")
        print(f"   Post-notes: {'✅ Yes' if book.get('notes_on_outline_after') else '⚪ Empty'}")
        print(f"   Status: {book.get('status_outline_notes', 'N/A')}")
        
        print(f"\n📖 Chapters:")
        chapters = self.db.get_book_chapters(book['id'])
        if chapters:
            for ch in chapters:
                icon = "✅" if ch.get('status') == 'approved' else ("🔄" if ch.get('content') else "⏳")
                print(f"   {icon} Ch {ch['chapter_number']}: {ch.get('title', 'Untitled')[:40]}")
                print(f"      Status: {ch.get('status')} | Notes: {ch.get('notes_status')}")
        else:
            print("   No chapters initialized")
        
        print(f"\n📄 Compilation:")
        print(f"   Final Review: {book.get('final_review_notes_status', 'N/A')}")
        print(f"   Output Status: {book.get('book_output_status', 'N/A')}")


# ==========================================================================
# CLI INTERFACE
# ==========================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Book Generation System - Automated book creation with LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # process - Process input file
    process_parser = subparsers.add_parser('process', help='Process input Excel file')
    
    # outlines - Generate outlines
    outline_parser = subparsers.add_parser('outlines', help='Generate outlines for pending books')
    
    # chapters - Generate chapters
    chapters_parser = subparsers.add_parser('chapters', help='Generate chapters for a book')
    chapters_parser.add_argument('book_id', help='Book ID')
    chapters_parser.add_argument('--auto-approve', action='store_true', help='Auto-approve all chapters')
    
    # compile - Compile book
    compile_parser = subparsers.add_parser('compile', help='Compile book to output files')
    compile_parser.add_argument('book_id', help='Book ID')
    compile_parser.add_argument('--formats', nargs='+', choices=['docx', 'pdf', 'txt'], help='Output formats')
    compile_parser.add_argument('--force', action='store_true', help='Force compile even if not all approved')
    
    # run - Run full pipeline
    run_parser = subparsers.add_parser('run', help='Run full pipeline for a book')
    run_parser.add_argument('--book-id', help='Specific book ID')
    run_parser.add_argument('--auto-approve', action='store_true', help='Auto-approve all stages')
    
    # status - Show status
    status_parser = subparsers.add_parser('status', help='Show status of all books')
    
    # details - Show book details
    details_parser = subparsers.add_parser('details', help='Show detailed book info')
    details_parser.add_argument('book_id', help='Book ID')
    
    # approve - Approve outline or chapter
    approve_parser = subparsers.add_parser('approve', help='Approve outline or chapter')
    approve_parser.add_argument('type', choices=['outline', 'chapter'], help='What to approve')
    approve_parser.add_argument('id', help='Book ID (for outline) or Chapter ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    orchestrator = BookGenerationOrchestrator()
    
    if args.command == 'process':
        orchestrator.process_input()
        orchestrator.generate_outlines()
    
    elif args.command == 'outlines':
        orchestrator.generate_outlines()
    
    elif args.command == 'chapters':
        orchestrator.generate_chapters(args.book_id, args.auto_approve)
    
    elif args.command == 'compile':
        orchestrator.compile_book(args.book_id, args.formats, args.force)
    
    elif args.command == 'run':
        orchestrator.run_full_pipeline(args.book_id, args.auto_approve)
    
    elif args.command == 'status':
        orchestrator.show_status()
    
    elif args.command == 'details':
        orchestrator.show_book_details(args.book_id)
    
    elif args.command == 'approve':
        if args.type == 'outline':
            orchestrator.outline_gen.approve_outline(args.id, needs_notes=False)
            print(f"✅ Outline approved for book: {args.id}")
        else:
            orchestrator.chapter_gen.approve_chapter(args.id)
            print(f"✅ Chapter approved: {args.id}")


if __name__ == "__main__":
    main()
