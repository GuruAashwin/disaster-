"""
Notification service for sending alerts to family members when matches are verified.
Supports: Email, SMS (via environment variables), and in-app logs.
"""

import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Notification log file (for demo/dev - replace with actual SMS/Email service)
NOTIFICATIONS_LOG = Path(__file__).parent.parent / "notifications.log"


def send_match_notification(
    contact_phone: Optional[str],
    contact_email: Optional[str],
    missing_person_name: str,
    found_person_shelter: str,
    found_person_condition: str,
) -> dict:
    """
    Send notification to family member when a match is verified.
    
    Args:
        contact_phone: Phone number of family member
        contact_email: Email of family member
        missing_person_name: Name of missing person from report
        found_person_shelter: Shelter/location where person was found
        found_person_condition: Medical/condition status
    
    Returns:
        dict with status and details of notifications sent
    """
    
    if not contact_phone and not contact_email:
        logger.warning("No contact details provided for notification")
        return {"status": "failed", "reason": "No contact details available"}
    
    sent_via = []
    
    # Prepare message
    message = f"""
🛡️ DISASTER RESPONSE - MATCH FOUND NOTIFICATION 🛡️

Good news! Your missing family member has been found.

👤 Person: {missing_person_name}
📍 Location: {found_person_shelter}
⚕️ Condition: {found_person_condition}

Please contact the police for further details and verification.

Stay safe!
"""
    
    # Send via Email (placeholder - implement with actual email service)
    if contact_email:
        try:
            _send_email_notification(
                email=contact_email,
                subject="🛡️ Your Missing Family Member Has Been Found",
                body=message
            )
            sent_via.append("email")
            logger.info(f"Email notification sent to {contact_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {contact_email}: {str(e)}")
    
    # Send via SMS (placeholder - implement with Twilio, AWS SNS, or local SMS service)
    if contact_phone:
        try:
            _send_sms_notification(
                phone=contact_phone,
                message=message
            )
            sent_via.append("sms")
            logger.info(f"SMS notification sent to {contact_phone}")
        except Exception as e:
            logger.error(f"Failed to send SMS to {contact_phone}: {str(e)}")
    
    # Log to file for audit trail
    _log_notification(
        contact_phone=contact_phone,
        contact_email=contact_email,
        missing_person_name=missing_person_name,
        shelter=found_person_shelter,
        condition=found_person_condition,
        sent_via=sent_via
    )
    
    return {
        "status": "success" if sent_via else "failed",
        "sent_via": sent_via,
        "message": "Notification sent" if sent_via else "Failed to send notification"
    }


def _send_email_notification(email: str, subject: str, body: str) -> None:
    """
    Send email notification.
    
    Placeholder implementation. In production, use:
    - AWS SES
    - SendGrid
    - Twilio SendGrid
    - etc.
    """
    logger.info(f"[EMAIL] To: {email}")
    logger.info(f"[EMAIL] Subject: {subject}")
    logger.info(f"[EMAIL] Body: {body[:100]}...")
    
    # TODO: Implement actual email sending
    # For now, just log it


def _send_sms_notification(phone: str, message: str) -> None:
    """
    Send SMS notification.
    
    Placeholder implementation. In production, use:
    - Twilio
    - AWS SNS
    - Vonage/Nexmo
    - etc.
    """
    logger.info(f"[SMS] To: {phone}")
    logger.info(f"[SMS] Message: {message[:100]}...")
    
    # TODO: Implement actual SMS sending
    # For now, just log it


def _log_notification(
    contact_phone: Optional[str],
    contact_email: Optional[str],
    missing_person_name: str,
    shelter: str,
    condition: str,
    sent_via: list
) -> None:
    """Log notification to file for audit trail."""
    import json
    from datetime import datetime
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "contact_phone": contact_phone,
        "contact_email": contact_email,
        "missing_person_name": missing_person_name,
        "shelter": shelter,
        "condition": condition,
        "sent_via": sent_via,
        "status": "sent" if sent_via else "failed"
    }
    
    try:
        with open(NOTIFICATIONS_LOG, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to log notification: {str(e)}")
