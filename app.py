"""
📚 Book Generation System - Web Dashboard
A user-friendly interface with guided workflow for book generation.
Run with: streamlit run app.py
"""

import streamlit as st
import time
from datetime import datetime

from config import Config
from database import Database
from input_handler import InputHandler, create_sample_input
from outline_generator import OutlineGenerator
from chapter_generator import ChapterGenerator
from compiler import BookCompiler
from notifications import NotificationService


# Page configuration
st.set_page_config(
    page_title="📚 AI Book Generator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize services
@st.cache_resource
def init_services():
    return {
        'db': Database(),
        'outline_gen': OutlineGenerator(),
        'chapter_gen': ChapterGenerator(),
        'compiler': BookCompiler(),
        'notifier': NotificationService()
    }

services = init_services()


# Custom CSS for better styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.8rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .step-card {
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        margin: 1rem 0;
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
    }
    .step-active {
        border-color: #667eea;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .step-complete {
        border-color: #28a745;
        background: linear-gradient(145deg, #f0fff4 0%, #e8f5e9 100%);
    }
    .step-number {
        display: inline-block;
        width: 36px;
        height: 36px;
        line-height: 36px;
        text-align: center;
        border-radius: 50%;
        background: #667eea;
        color: white;
        font-weight: bold;
        margin-right: 10px;
    }
    .hint-box {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    .big-button {
        font-size: 1.2rem !important;
        padding: 0.8rem 2rem !important;
    }
    .workflow-progress {
        display: flex;
        justify-content: space-between;
        margin: 2rem 0;
    }
    .progress-step {
        flex: 1;
        text-align: center;
        padding: 0.5rem;
        position: relative;
    }
    .progress-step::after {
        content: '';
        position: absolute;
        top: 50%;
        right: 0;
        width: 100%;
        height: 2px;
        background: #e0e0e0;
        z-index: -1;
    }
</style>
""", unsafe_allow_html=True)


def get_workflow_state():
    """Calculate current workflow state based on database."""
    books = services['db'].get_all_books()
    
    if not books:
        return {
            'step': 1,
            'message': "Let's start by adding your first book!",
            'books': []
        }
    
    # Check for books without outlines
    needs_outline = [b for b in books if not b.get('outline')]
    if needs_outline:
        return {
            'step': 2,
            'message': f"{len(needs_outline)} book(s) need outlines generated.",
            'books': books,
            'pending': needs_outline
        }
    
    # Check for books with outlines needing approval
    needs_approval = [b for b in books if b.get('outline') and b.get('status_outline_notes') == 'yes']
    if needs_approval:
        return {
            'step': 2,
            'message': f"{len(needs_approval)} outline(s) ready for your review!",
            'books': books,
            'pending': needs_approval
        }
    
    # Check for books ready for chapters
    ready_for_chapters = [b for b in books if b.get('status_outline_notes') == 'no_notes_needed']
    books_needing_chapters = []
    
    for book in ready_for_chapters:
        chapters = services['db'].get_book_chapters(book['id'])
        if not chapters:
            books_needing_chapters.append(book)
        else:
            pending = [c for c in chapters if not c.get('content')]
            if pending:
                books_needing_chapters.append(book)
    
    if books_needing_chapters:
        return {
            'step': 3,
            'message': f"{len(books_needing_chapters)} book(s) ready for chapter generation!",
            'books': books,
            'pending': books_needing_chapters
        }
    
    # Check for books ready for compilation
    ready_for_compile = [b for b in books if b.get('book_output_status') != 'completed' and b.get('status_outline_notes') == 'no_notes_needed']
    if ready_for_compile:
        return {
            'step': 4,
            'message': f"{len(ready_for_compile)} book(s) ready to be compiled!",
            'books': books,
            'pending': ready_for_compile
        }
    
    return {
        'step': 5,
        'message': "All books are complete! 🎉",
        'books': books,
        'pending': []
    }


def main():
    # Header
    st.markdown('<p class="main-title">📚 AI Book Generator</p>', unsafe_allow_html=True)
    st.caption("Generate complete books with AI in 4 simple steps")
    
    # Get current workflow state
    state = get_workflow_state()
    
    # Workflow progress bar
    show_workflow_progress(state['step'])
    
    st.markdown("---")
    
    # Sidebar navigation
    with st.sidebar:
        st.title("📖 Navigation")
        
        # Show current status
        st.markdown("### 📊 Current Status")
        st.info(state['message'])
        
        st.markdown("---")
        
        # Navigation based on workflow
        if state['step'] == 1:
            page = st.radio("Go to:", ["🏠 Home", "➕ Add Book"], index=0)
        else:
            page = st.radio(
                "Go to:",
                ["🏠 Home", "➕ Add Book", "📝 Outlines", "📖 Chapters", "📄 Compile", "⚙️ Settings"],
                index=0
            )
        
        st.markdown("---")
        st.markdown("### 💡 Quick Tips")
        st.caption("• Follow the numbered steps")
        st.caption("• Green = Complete")
        st.caption("• Blue = Current step")
        st.caption("• Gray = Upcoming")
    
    # Main content based on page
    if page == "🏠 Home":
        show_home_page(state)
    elif page == "➕ Add Book":
        show_add_book_page()
    elif page == "📝 Outlines":
        show_outlines_page()
    elif page == "📖 Chapters":
        show_chapters_page()
    elif page == "📄 Compile":
        show_compile_page()
    elif page == "⚙️ Settings":
        show_settings_page()


def show_workflow_progress(current_step):
    """Show visual workflow progress."""
    steps = ["Add Book", "Generate Outline", "Write Chapters", "Compile Book"]
    
    cols = st.columns(4)
    for i, (col, step) in enumerate(zip(cols, steps), 1):
        with col:
            if i < current_step:
                st.success(f"✅ Step {i}")
                st.caption(step)
            elif i == current_step:
                st.info(f"👉 Step {i}")
                st.caption(f"**{step}**")
            else:
                st.empty()
                st.caption(f"Step {i}: {step}")


def show_home_page(state):
    """Show home page with guided workflow."""
    
    if state['step'] == 1:
        # No books yet - guide to add first book
        st.markdown("""
        <div class="hint-box" style="background-color: Black;">
            <h3>👋 Welcome to AI Book Generator!</h3>
            <p>This tool helps you create complete books using AI. Here's how it works:</p>
            <ol>
                <li><strong>Add a Book</strong> - Enter your book title and describe what you want</li>
                <li><strong>Generate Outline</strong> - AI creates a detailed chapter outline</li>
                <li><strong>Write Chapters</strong> - AI writes each chapter (you can review & edit)</li>
                <li><strong>Compile Book</strong> - Export to DOCX, PDF, or TXT format</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🚀 Let's Get Started!")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("➕ Add Your First Book", type="primary", use_container_width=True):
                st.session_state['page'] = 'add'
                st.rerun()
    
    else:
        # Show dashboard for existing books
        st.markdown("### 📊 Your Books")
        
        # Quick action based on current step
        if state.get('pending'):
            st.markdown(f"""
            <div class="hint-box" style="background-color: Black;">
                <h4>👉 Next Action Required</h4>
                <p>{state['message']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Book cards
        for book in state['books']:
            show_book_card(book)


def show_book_card(book):
    """Display a book as a card with status and actions."""
    chapters = services['db'].get_book_chapters(book['id'])
    generated = len([c for c in chapters if c.get('content')]) if chapters else 0
    total = len(chapters) if chapters else 0
    
    # Determine status
    if book.get('book_output_status') == 'completed':
        status_color = "🟢"
        status_text = "Complete"
    elif generated == total and total > 0:
        status_color = "🟡"
        status_text = "Ready to Compile"
    elif book.get('status_outline_notes') == 'no_notes_needed':
        status_color = "🔵"
        status_text = f"Chapters: {generated}/{total}"
    elif book.get('outline'):
        status_color = "🟠"
        status_text = "Outline Ready for Review"
    else:
        status_color = "⚪"
        status_text = "Needs Outline"
    
    with st.expander(f"{status_color} **{book['title']}** - {status_text}", expanded=False):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if book.get('outline'):
                st.text_area("Outline Preview", book['outline'][:500] + "...", height=100, disabled=True)
            
            if chapters:
                progress = generated / total if total > 0 else 0
                st.progress(progress)
                st.caption(f"Chapters: {generated}/{total} complete")
        
        with col2:
            # Show relevant action button
            if not book.get('outline'):
                if st.button("🤖 Generate Outline", key=f"gen_out_{book['id']}", type="primary"):
                    with st.spinner("AI is creating your outline..."):
                        outline = services['outline_gen'].llm.generate_outline(
                            book['title'],
                            book['notes_on_outline_before']
                        )
                        services['db'].update_book(book['id'], outline=outline, status_outline_notes='yes')
                        # Send notification
                        services['notifier'].notify_outline_ready(book['id'])
                    st.success("✅ Outline generated! Notification sent.")
                    st.rerun()
            
            elif book.get('status_outline_notes') != 'no_notes_needed':
                if st.button("✅ Approve Outline", key=f"approve_{book['id']}", type="primary"):
                    services['db'].update_book(book['id'], status_outline_notes='no_notes_needed')
                    st.rerun()
            
            elif not chapters or generated < total:
                if st.button("📖 Generate Chapters", key=f"gen_ch_{book['id']}", type="primary"):
                    st.session_state['selected_book'] = book['id']
                    st.session_state['page'] = 'chapters'
                    st.rerun()
            
            elif book.get('book_output_status') != 'completed':
                if st.button("📄 Compile Book", key=f"compile_{book['id']}", type="primary"):
                    with st.spinner("Compiling your book..."):
                        results = services['compiler'].compile_book(book['id'], force=True)
                    st.success("✅ Book compiled!")
                    st.rerun()
            
            else:
                st.success("✅ Complete!")
                if book.get('output_docx_path'):
                    st.caption(f"📄 Files saved in output folder")


def show_add_book_page():
    """Page to add a new book."""
    st.markdown("## ➕ Add New Book")
    
    st.markdown("""
    <div class="hint-box" style="background-color: Black;">
        <h4>💡 How to describe your book</h4>
        <p>Tell the AI what you want your book to cover:</p>
        <ul>
            <li>Who is the target audience?</li>
            <li>What topics should be covered?</li>
            <li>What's the tone/style? (Professional, casual, academic...)</li>
            <li>Any specific requirements or focuses?</li>
        </ul>
        <p><em>The more detail you provide, the better your book will be!</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("add_book_form"):
        title = st.text_input(
            "📖 Book Title",
            placeholder="e.g., 'Mastering Python for Data Science'",
            help="Choose a clear, descriptive title for your book"
        )
        
        notes = st.text_area(
            "📝 Book Description & Requirements",
            placeholder="""Example:
- Target audience: Beginners with some programming experience
- Focus on practical, hands-on examples
- Cover: data types, pandas, visualization, basic ML
- Tone: Friendly and encouraging
- Include exercises at the end of each chapter""",
            height=200,
            help="Describe what you want the book to cover"
        )
        
        col1, col2 = st.columns([3, 1])
        with col2:
            auto_generate = st.checkbox("🚀 Auto-generate outline", value=True, help="Automatically generate the outline after adding")
        
        submitted = st.form_submit_button("➕ Create Book", type="primary", use_container_width=True)
        
        if submitted:
            if not title:
                st.error("❌ Please enter a book title!")
            elif not notes:
                st.error("❌ Please describe your book requirements!")
            else:
                with st.spinner("Creating your book..."):
                    book = services['db'].create_book(title=title, notes_on_outline_before=notes)
                    
                    if auto_generate:
                        st.info("🤖 Generating outline with AI...")
                        outline = services['outline_gen'].llm.generate_outline(title, notes)
                        services['db'].update_book(book['id'], outline=outline, status_outline_notes='yes')
                        # Send notification
                        services['notifier'].notify_outline_ready(book['id'])
                        st.success("✅ Book created and outline generated! Notification sent.")
                    else:
                        st.success("✅ Book created! Generate the outline when you're ready.")
                
                time.sleep(1)
                st.rerun()


def show_outlines_page():
    """Page to manage book outlines."""
    st.markdown("## 📝 Manage Outlines")
    
    st.markdown("""
    <div class="hint-box" style="background-color: Black;">
        <h4>📖 What to do here</h4>
        <p>Review each outline and either:</p>
        <ul>
            <li>✅ <strong>Approve</strong> - If you're happy with the outline</li>
            <li>🔄 <strong>Regenerate</strong> - If you want changes (add feedback first)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    books = services['db'].get_all_books()
    books_with_outlines = [b for b in books if b.get('outline')]
    
    if not books_with_outlines:
        st.warning("No outlines yet. Add a book first!")
        return
    
    for book in books_with_outlines:
        is_approved = book.get('status_outline_notes') == 'no_notes_needed'
        icon = "✅" if is_approved else "📝"
        
        with st.expander(f"{icon} {book['title']}", expanded=not is_approved):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown("### 📋 Outline")
                st.markdown(book['outline'])
            
            with col2:
                if is_approved:
                    st.success("✅ **Approved**")
                    st.caption("Ready for chapter generation")
                else:
                    st.warning("⏳ **Needs Review**")
                    
                    if st.button("✅ Approve & Continue", key=f"approve_{book['id']}", type="primary", use_container_width=True):
                        services['db'].update_book(book['id'], status_outline_notes='no_notes_needed')
                        st.success("Approved! Moving to chapters...")
                        time.sleep(1)
                        st.rerun()
                    
                    st.markdown("---")
                    st.markdown("**Or request changes:**")
                    feedback = st.text_area("Your feedback:", key=f"fb_{book['id']}", height=100, placeholder="What would you like changed?")
                    
                    if st.button("🔄 Regenerate", key=f"regen_{book['id']}", use_container_width=True):
                        if feedback:
                            with st.spinner("AI is revising the outline..."):
                                new_outline = services['outline_gen'].llm.regenerate_outline(
                                    book['title'], book['outline'], feedback
                                )
                                services['db'].update_book(book['id'], outline=new_outline)
                            st.success("Outline updated!")
                            st.rerun()
                        else:
                            st.error("Please provide feedback first!")


def show_chapters_page():
    """Page to manage chapters."""
    st.markdown("## 📖 Generate Chapters")
    
    # Get books ready for chapters
    books = services['db'].get_all_books()
    ready_books = [b for b in books if b.get('status_outline_notes') == 'no_notes_needed']
    
    if not ready_books:
        st.warning("⚠️ No books with approved outlines yet. Approve an outline first!")
        return
    
    st.markdown("""
    <div class="hint-box" style="background-color: Black;">
        <h4>📖 How chapter generation works</h4>
        <ul>
            <li>Each chapter is generated based on your outline</li>
            <li>Later chapters use summaries from earlier chapters for context</li>
            <li>You can generate all at once or one at a time</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Book selection
    book_names = {b['title']: b['id'] for b in ready_books}
    selected = st.selectbox("Select a book:", list(book_names.keys()))
    book_id = book_names[selected]
    book = services['db'].get_book(book_id)
    
    st.markdown("---")
    
    chapters = services['db'].get_book_chapters(book_id)
    
    # Initialize if needed
    if not chapters:
        st.info("📚 Chapters haven't been initialized yet.")
        if st.button("📋 Initialize Chapters from Outline", type="primary"):
            with st.spinner("Parsing outline into chapters..."):
                chapters = services['chapter_gen'].initialize_chapters_for_book(book_id)
            st.success(f"✅ Found {len(chapters)} chapters!")
            st.rerun()
        return
    
    # Progress
    generated = len([c for c in chapters if c.get('content')])
    approved = len([c for c in chapters if c.get('status') == 'approved'])
    total = len(chapters)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📖 Total Chapters", total)
    col2.metric("✏️ Generated", f"{generated}/{total}")
    col3.metric("✅ Approved", f"{approved}/{total}")
    
    st.progress(generated / total if total > 0 else 0)
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        pending = [c for c in chapters if not c.get('content')]
        if pending:
            if st.button(f"🤖 Generate All {len(pending)} Pending Chapters", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, chapter in enumerate(pending):
                    status_text.info(f"✍️ Writing Chapter {chapter['chapter_number']}: {chapter.get('title', '')[:30]}...")
                    services['chapter_gen'].generate_chapter(book_id, chapter['chapter_number'])
                    progress_bar.progress((i + 1) / len(pending))
                
                # Send notification
                services['notifier'].notify(
                    "chapters_generated", 
                    book_id, 
                    f"All {len(pending)} chapters have been generated and are ready for review."
                )
                status_text.success(f"✅ All {len(pending)} chapters generated! Notification sent.")
                time.sleep(1)
                st.rerun()
        else:
            st.success("✅ All chapters generated!")
    
    with col2:
        unapproved = [c for c in chapters if c.get('content') and c.get('status') != 'approved']
        if unapproved:
            if st.button(f"✅ Approve All {len(unapproved)} Chapters", type="secondary", use_container_width=True):
                for chapter in unapproved:
                    services['chapter_gen'].approve_chapter(chapter['id'])
                st.success("All chapters approved!")
                st.rerun()
    
    # Individual chapters
    st.markdown("### 📚 Chapters")
    
    for chapter in chapters:
        has_content = bool(chapter.get('content'))
        is_approved = chapter.get('status') == 'approved'
        
        icon = "✅" if is_approved else ("📝" if has_content else "⏳")
        status = "Approved" if is_approved else ("Ready for Review" if has_content else "Pending")
        
        with st.expander(f"{icon} Chapter {chapter['chapter_number']}: {chapter.get('title', 'Untitled')[:40]} — *{status}*"):
            if has_content:
                content = chapter['content']
                st.text_area("Content", content[:3000] + ("..." if len(content) > 3000 else ""), height=200, disabled=True, label_visibility="collapsed")
                
                if chapter.get('summary'):
                    st.info(f"**Summary:** {chapter['summary']}")
                
                if not is_approved:
                    if st.button("✅ Approve Chapter", key=f"approve_ch_{chapter['id']}"):
                        services['chapter_gen'].approve_chapter(chapter['id'])
                        st.rerun()
            else:
                st.caption("Not generated yet")
                if st.button("🤖 Generate This Chapter", key=f"gen_ch_{chapter['id']}"):
                    with st.spinner(f"Writing Chapter {chapter['chapter_number']}..."):
                        services['chapter_gen'].generate_chapter(book_id, chapter['chapter_number'])
                    st.rerun()


def show_compile_page():
    """Page to compile books."""
    st.markdown("## 📄 Compile Your Book")
    
    st.markdown("""
    <div class="hint-box" style="background-color: Black;">
        <h4>📤 Export your finished book</h4>
        <p>Choose your format(s) and download your complete book:</p>
        <ul>
            <li>📝 <strong>DOCX</strong> - Edit in Microsoft Word</li>
            <li>📕 <strong>PDF</strong> - Share and print</li>
            <li>📋 <strong>TXT</strong> - Plain text format</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    books = services['db'].get_all_books()
    
    for book in books:
        chapters = services['db'].get_book_chapters(book['id'])
        generated = len([c for c in chapters if c.get('content')]) if chapters else 0
        
        is_complete = book.get('book_output_status') == 'completed'
        icon = "✅" if is_complete else "📖"
        
        with st.expander(f"{icon} {book['title']}", expanded=not is_complete):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Chapters generated:** {generated}/{len(chapters) if chapters else 0}")
                
                if is_complete:
                    st.success("✅ Book compiled successfully!")
                    
                    if book.get('output_docx_path'):
                        st.write(f"📝 **DOCX:** `{book['output_docx_path']}`")
                    if book.get('output_pdf_path'):
                        st.write(f"📕 **PDF:** `{book['output_pdf_path']}`")
                    if book.get('output_txt_path'):
                        st.write(f"📋 **TXT:** `{book['output_txt_path']}`")
                    
                    st.caption("Files are saved in the `output` folder")
            
            with col2:
                formats = st.multiselect(
                    "Formats:",
                    ["docx", "pdf", "txt"],
                    default=["docx", "pdf"],
                    key=f"fmt_{book['id']}"
                )
                
                if st.button("📄 Compile Now", key=f"compile_{book['id']}", type="primary", use_container_width=True):
                    with st.spinner("Creating your book files..."):
                        results = services['compiler'].compile_book(book['id'], formats, force=True)
                        services['notifier'].notify_final_draft_ready(book['id'], results)
                    st.success("🎉 Book compiled! Check the output folder.")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()


def show_settings_page():
    """Settings and configuration page."""
    st.markdown("## ⚙️ Settings & Configuration")
    
    # AI Model
    st.markdown("### 🤖 AI Model")
    st.write(f"**Model:** `{Config.GEMINI_MODEL}`")
    
    # Notifications
    st.markdown("### 🔔 Notifications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📧 Email**")
        email_ok = Config.SMTP_USER and '@' in Config.SMTP_USER and Config.SMTP_PASSWORD
        if email_ok:
            st.success(f"✅ Configured ({Config.SMTP_USER})")
        else:
            st.warning("❌ Not configured")
            st.caption("Edit `.env` file to add SMTP credentials")
    
    with col2:
        st.markdown("**🔗 MS Teams**")
        teams_ok = Config.TEAMS_WEBHOOK_URL and 'your-webhook' not in Config.TEAMS_WEBHOOK_URL.lower()
        if teams_ok:
            st.success("✅ Configured")
        else:
            st.warning("❌ Not configured")
            st.caption("Edit `.env` file to add Teams webhook")
    
    # Test notifications
    st.markdown("---")
    st.markdown("### 🧪 Test Notifications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📧 Send Test Email", disabled=not email_ok):
            result = services['notifier'].send_email("Test", "This is a test from Book Generator!")
            if result.get('success'):
                st.success("✅ Email sent!")
            else:
                st.error(f"❌ {result.get('error')}")
    
    with col2:
        if st.button("🔗 Send Test Teams", disabled=not teams_ok):
            result = services['notifier'].send_teams_notification("Test", "🧪 Test Message")
            if result.get('success'):
                st.success("✅ Teams message sent!")
            else:
                st.error(f"❌ {result.get('error')}")
    
    # Paths
    st.markdown("---")
    st.markdown("### 📁 File Locations")
    st.code(f"Input folder: {Config.INPUT_DIR}\nOutput folder: {Config.OUTPUT_DIR}")


if __name__ == "__main__":
    main()
