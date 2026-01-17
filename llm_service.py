"""
LLM Service module for the Book Generation System.
Handles all Gemini API interactions for generating outlines, chapters, and summaries.
Uses the new google-genai package (recommended over deprecated google-generativeai).
"""

from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types
from config import Config


class LLMService:
    """Google Gemini LLM service for book generation."""
    
    def __init__(self):
        """Initialize Gemini client."""
        if not Config.GEMINI_API_KEY:
            raise ValueError("Gemini API key must be set in .env file")
        
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.model = Config.GEMINI_MODEL
    
    def _generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generate text using Gemini."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=0.7,
            )
        )
        return response.text
    
    # ==========================================================================
    # OUTLINE GENERATION
    # ==========================================================================
    
    def generate_outline(self, title: str, notes: str) -> str:
        """
        Generate a book outline based on title and notes.
        
        Args:
            title: Book title
            notes: Pre-outline notes from editor
            
        Returns:
            Generated outline as markdown string
        """
        prompt = f"""You are an expert book author and editor. Your task is to create a detailed book outline.

BOOK TITLE: {title}

EDITOR'S NOTES & REQUIREMENTS:
{notes}

Please generate a comprehensive book outline with the following structure:
1. An engaging introduction section
2. Main chapters (aim for 8-12 chapters depending on scope)
3. A conclusion/summary section

For each chapter, provide:
- Chapter number and title
- Brief description (2-3 sentences) of what the chapter will cover
- Key topics/subtopics as bullet points

Format the outline in clear markdown with proper headings.

IMPORTANT: Consider the editor's notes carefully when designing the structure and focus of each chapter.

Generate the outline now:"""

        return self._generate(prompt, max_tokens=4096)
    
    def regenerate_outline(self, title: str, original_outline: str, feedback: str) -> str:
        """
        Regenerate outline based on editor feedback.
        
        Args:
            title: Book title
            original_outline: Previously generated outline
            feedback: Editor's notes/feedback for improvement
            
        Returns:
            Improved outline
        """
        prompt = f"""You are an expert book author and editor. You need to revise a book outline based on feedback.

BOOK TITLE: {title}

ORIGINAL OUTLINE:
{original_outline}

EDITOR'S FEEDBACK FOR IMPROVEMENT:
{feedback}

Please revise the outline to address all the feedback. Maintain the same general format but incorporate the requested changes.

Generate the improved outline now:"""

        return self._generate(prompt, max_tokens=4096)
    
    # ==========================================================================
    # CHAPTER GENERATION
    # ==========================================================================
    
    def generate_chapter(
        self,
        title: str,
        outline: str,
        chapter_number: int,
        chapter_title: str,
        previous_summaries: List[Dict[str, str]],
        chapter_notes: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate a chapter with context from previous chapters.
        
        Args:
            title: Book title
            outline: Full book outline
            chapter_number: Current chapter number
            chapter_title: Title of the chapter to generate
            previous_summaries: List of dicts with 'chapter_number', 'title', 'summary'
            chapter_notes: Optional editor notes for this chapter
            
        Returns:
            Dict with 'content' and 'summary' keys
        """
        # Build context from previous chapters
        context = ""
        if previous_summaries:
            context = "SUMMARY OF PREVIOUS CHAPTERS:\n"
            for ch in previous_summaries:
                context += f"\nChapter {ch['chapter_number']}: {ch.get('title', 'Untitled')}\n"
                context += f"{ch.get('summary', 'No summary available.')}\n"
        
        notes_section = ""
        if chapter_notes:
            notes_section = f"\nEDITOR'S NOTES FOR THIS CHAPTER:\n{chapter_notes}\n"
        
        prompt = f"""You are an expert book author writing a chapter for a book.

BOOK TITLE: {title}

BOOK OUTLINE:
{outline}

{context}

CHAPTER TO WRITE: Chapter {chapter_number}: {chapter_title}
{notes_section}

Write this chapter in a professional, engaging style that:
1. Flows naturally from previous chapters (if any)
2. Covers the topics mentioned in the outline for this chapter
3. Uses clear explanations and examples where appropriate
4. Maintains consistent tone with the book's overall style
5. Is approximately 2000-3000 words

Write the complete chapter now:"""

        content = self._generate(prompt, max_tokens=8192)
        
        # Generate summary for context chaining
        summary = self._generate_chapter_summary(title, chapter_number, chapter_title, content)
        
        return {
            "content": content,
            "summary": summary
        }
    
    def _generate_chapter_summary(
        self, 
        title: str,
        chapter_number: int,
        chapter_title: str,
        content: str
    ) -> str:
        """Generate a concise summary of a chapter for context chaining."""
        prompt = f"""Summarize the following chapter in 3-5 sentences. Focus on the main points, key concepts, and any important conclusions.

BOOK: {title}
CHAPTER {chapter_number}: {chapter_title}

CHAPTER CONTENT:
{content[:8000]}

Provide a concise summary:"""

        return self._generate(prompt, max_tokens=500)
    
    def regenerate_chapter(
        self,
        title: str,
        chapter_number: int,
        chapter_title: str,
        original_content: str,
        feedback: str
    ) -> Dict[str, str]:
        """Regenerate a chapter based on editor feedback."""
        prompt = f"""You are revising a chapter based on editor feedback.

BOOK: {title}
CHAPTER {chapter_number}: {chapter_title}

ORIGINAL CHAPTER:
{original_content}

EDITOR'S FEEDBACK:
{feedback}

Revise the chapter to address all feedback while maintaining the overall flow and style.

Generate the revised chapter:"""

        content = self._generate(prompt, max_tokens=8192)
        summary = self._generate_chapter_summary(title, chapter_number, chapter_title, content)
        
        return {
            "content": content,
            "summary": summary
        }


# ==========================================================================
# TEST
# ==========================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("LLM SERVICE TEST")
    print("=" * 60)
    
    try:
        llm = LLMService()
        print(f"✅ LLM Service initialized with model: {Config.GEMINI_MODEL}")
        
        # Test outline generation
        print("\n📝 Testing outline generation...")
        test_title = "Introduction to Machine Learning"
        test_notes = "Target audience: beginners with basic Python knowledge. Cover supervised and unsupervised learning. Include practical examples."
        
        outline = llm.generate_outline(test_title, test_notes)
        print(f"\n✅ Outline generated ({len(outline)} characters)")
        print("\n--- OUTLINE PREVIEW ---")
        print(outline[:1000] + "..." if len(outline) > 1000 else outline)
        print("--- END PREVIEW ---")
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
