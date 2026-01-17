"""
Notification module for the Book Generation System.
Handles email notifications and optional MS Teams webhooks.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
import requests

from database import Database
from config import Config


class NotificationService:
    """Handles notifications via Email and MS Teams."""
    
    def __init__(self):
        """Initialize notification service."""
        self.db = Database()
    
    # ==========================================================================
    # EMAIL NOTIFICATIONS
    # ==========================================================================
    
    def send_email(
        self, 
        subject: str, 
        body: str, 
        to_email: Optional[str] = None,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email notification via SMTP.
        
        Args:
            subject: Email subject
            body: Plain text body
            to_email: Recipient email (defaults to NOTIFICATION_EMAIL)
            html_body: Optional HTML body
            
        Returns:
            Status dict with success/failure
        """
        to_email = to_email or Config.NOTIFICATION_EMAIL
        
        if not all([Config.SMTP_USER, Config.SMTP_PASSWORD, to_email]):
            return {
                "success": False,
                "error": "Email configuration incomplete. Check SMTP_USER, SMTP_PASSWORD, NOTIFICATION_EMAIL"
            }
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = Config.SMTP_USER
            msg['To'] = to_email
            
            # Attach plain text
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach HTML if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Connect and send
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.send_message(msg)
            
            return {"success": True, "message": f"Email sent to {to_email}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================================================
    # MS TEAMS NOTIFICATIONS
    # ==========================================================================
    
    def send_teams_notification(self, message: str, title: Optional[str] = None) -> Dict[str, Any]:
        """
        Send notification to MS Teams via webhook.
        Supports both legacy Connectors and new Power Automate Workflows.
        
        Args:
            message: Notification message
            title: Optional title
            
        Returns:
            Status dict with success/failure
        """
        webhook_url = Config.TEAMS_WEBHOOK_URL
        
        if not webhook_url or 'your-webhook' in webhook_url.lower():
            return {
                "success": False,
                "error": "MS Teams webhook not configured"
            }
        
        try:
            # Detect webhook type based on URL pattern
            is_workflow = (
                'logic.azure.com' in webhook_url or 
                'prod-' in webhook_url or
                'powerplatform.com' in webhook_url
            )
            
            if is_workflow:
                # New Power Automate Workflow format (Adaptive Card)
                payload = {
                    "type": "message",
                    "attachments": [
                        {
                            "contentType": "application/vnd.microsoft.card.adaptive",
                            "contentUrl": None,
                            "content": {
                                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                                "type": "AdaptiveCard",
                                "version": "1.4",
                                "body": [
                                    {
                                        "type": "TextBlock",
                                        "text": title or "📚 Book Generation Update",
                                        "weight": "Bolder",
                                        "size": "Large",
                                        "wrap": True,
                                        "color": "Accent"
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": message,
                                        "wrap": True,
                                        "spacing": "Medium"
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": "— Book Generation System",
                                        "size": "Small",
                                        "color": "Light",
                                        "spacing": "Large"
                                    }
                                ]
                            }
                        }
                    ]
                }
            else:
                # Legacy Connector format (MessageCard)
                payload = {
                    "@type": "MessageCard",
                    "@context": "http://schema.org/extensions",
                    "summary": title or "Book Generation System",
                    "themeColor": "0076D7",
                    "title": title or "📚 Book Generation Update",
                    "text": message
                }
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Power Automate workflows return 202 Accepted
            if response.status_code in [200, 202]:
                return {"success": True, "message": "Teams notification sent"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================================================
    # WORKFLOW NOTIFICATIONS
    # ==========================================================================
    
    def notify(
        self, 
        event_type: str, 
        book_id: str, 
        message: str,
        use_email: bool = True,
        use_teams: bool = False
    ) -> Dict[str, Any]:
        """
        Send notification and log to database.
        
        Args:
            event_type: Type of event (outline_ready, waiting_chapter_notes, etc.)
            book_id: Book ID
            message: Notification message
            use_email: Send via email
            use_teams: Send via Teams
            
        Returns:
            Status dict
        """
        book = self.db.get_book(book_id)
        book_title = book['title'] if book else "Unknown Book"
        
        results = {"email": None, "teams": None}
        
        # Prepare email content
        subject = f"[Book Generator] {event_type.replace('_', ' ').title()}: {book_title}"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>📚 {event_type.replace('_', ' ').title()}</h2>
            <p><strong>Book:</strong> {book_title}</p>
            <hr>
            <p>{message}</p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                This is an automated notification from the Book Generation System.
            </p>
        </body>
        </html>
        """
        
        # Send email
        if use_email:
            results["email"] = self.send_email(subject, message, html_body=html_body)
        
        # Send Teams
        if use_teams:
            results["teams"] = self.send_teams_notification(
                f"**{book_title}**\n\n{message}",
                title=f"📚 {event_type.replace('_', ' ').title()}"
            )
        
        # Log to database
        email_status = "sent" if results.get("email", {}).get("success") else "failed"
        self.db.log_notification(
            book_id=book_id,
            event_type=event_type,
            message=message,
            recipient=Config.NOTIFICATION_EMAIL,
            status=email_status
        )
        
        return results
    
    # ==========================================================================
    # PREDEFINED NOTIFICATIONS
    # ==========================================================================
    
    def notify_outline_ready(self, book_id: str) -> Dict[str, Any]:
        """Notify that outline is ready for review."""
        book = self.db.get_book(book_id)
        message = f"""
The outline for "{book['title']}" has been generated and is ready for your review.

Please review the outline in the database and:
- Add any notes in the 'notes_on_outline_after' field
- Set 'status_outline_notes' to 'no_notes_needed' to proceed to chapter generation
- Or set it to 'yes' if you need more time to review

Book ID: {book_id}
        """
        return self.notify("outline_ready", book_id, message.strip())
    
    def notify_waiting_chapter_notes(self, book_id: str, chapter_number: int) -> Dict[str, Any]:
        """Notify that a chapter is waiting for notes/approval."""
        book = self.db.get_book(book_id)
        message = f"""
Chapter {chapter_number} of "{book['title']}" has been generated and is waiting for your review.

Please review the chapter in the database and:
- Add any notes to improve the chapter
- Set the chapter's 'notes_status' to 'no_notes_needed' to approve

Book ID: {book_id}
        """
        return self.notify("waiting_chapter_notes", book_id, message.strip())
    
    def notify_chapter_ready(self, book_id: str, chapter_number: int) -> Dict[str, Any]:
        """Notify that a chapter has been generated."""
        book = self.db.get_book(book_id)
        message = f"""
Chapter {chapter_number} of "{book['title']}" has been successfully generated.

The chapter is now available in the database for review.

Book ID: {book_id}
        """
        return self.notify("chapter_ready", book_id, message.strip())
    
    def notify_final_draft_ready(self, book_id: str, output_paths: Dict[str, str]) -> Dict[str, Any]:
        """Notify that the final draft is compiled."""
        book = self.db.get_book(book_id)
        
        paths_text = "\n".join([
            f"- {fmt.upper()}: {path}" 
            for fmt, path in output_paths.items()
        ])
        
        message = f"""
🎉 The book "{book['title']}" has been compiled successfully!

Output files:
{paths_text}

The book is now complete and ready for use.

Book ID: {book_id}
        """
        return self.notify("final_draft_ready", book_id, message.strip())
    
    def notify_error(self, book_id: str, error_message: str) -> Dict[str, Any]:
        """Notify about an error or pause."""
        message = f"""
⚠️ The book generation workflow has encountered an issue:

{error_message}

Please check the database and resolve the issue to continue.

Book ID: {book_id}
        """
        return self.notify("error_pause", book_id, message.strip())
    
    def notify_book_completed(self, book_id: str) -> Dict[str, Any]:
        """Notify that the entire book is complete."""
        book = self.db.get_book(book_id)
        message = f"""
🎊 Congratulations! The book "{book['title']}" is now COMPLETE!

All chapters have been generated, reviewed, and the final draft has been compiled.

The book files are available in the output directory.

Book ID: {book_id}
        """
        return self.notify("book_completed", book_id, message.strip())


# ==========================================================================
# TEST
# ==========================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("NOTIFICATION SERVICE TEST")
    print("=" * 70)
    
    notifier = NotificationService()
    
    # Check configuration
    print("\n📧 Email Configuration:")
    print(f"   SMTP Host: {Config.SMTP_HOST}")
    print(f"   SMTP Port: {Config.SMTP_PORT}")
    print(f"   SMTP User: {'✅ Set' if Config.SMTP_USER and not Config.SMTP_USER.startswith('your') else '❌ Not configured'}")
    print(f"   SMTP Password: {'✅ Set' if Config.SMTP_PASSWORD and not Config.SMTP_PASSWORD.startswith('your') else '❌ Not configured'}")
    print(f"   Notification Email: {'✅ Set' if Config.NOTIFICATION_EMAIL and not Config.NOTIFICATION_EMAIL.startswith('recipient') else '❌ Not configured'}")
    
    print("\n🔗 Teams Configuration:")
    print(f"   Webhook: {'✅ Set' if Config.TEAMS_WEBHOOK_URL and not 'your-webhook' in Config.TEAMS_WEBHOOK_URL else '❌ Not configured'}")
    
    # Test with a book
    db = Database()
    books = db.get_all_books()
    
    if books:
        test_book = books[0]
        print(f"\n📚 Testing notifications for: {test_book['title']}")
        
        # Note: Won't actually send if email not configured
        print("\n📤 Testing outline_ready notification (will log to DB)...")
        result = notifier.notify_outline_ready(test_book['id'])
        
        if result['email'] and result['email'].get('success'):
            print("   ✅ Email sent successfully!")
        else:
            print(f"   ⚠️  Email: {result['email']}")
        
        # Check notification log
        logs = db.get_book_notifications(test_book['id'])
        print(f"\n📋 Notification log entries: {len(logs)}")
        for log in logs[:3]:
            print(f"   - {log['event_type']}: {log['status']} at {log['sent_at']}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
