import logging
from typing import Dict, Any, Optional
from celery import Task
from celery.exceptions import Retry
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


class BaseTask(Task):
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            f"Task {self.name}[{task_id}] failed: {exc}",
            exc_info=einfo
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {self.name}[{task_id}] succeeded")


@celery_app.task(
    bind=True,
    base=BaseTask,
    name='app.tasks.send_email',
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_email(self, recipient: str, subject: str, body: str, **kwargs) -> Dict[str, Any]:

    try:
        logger.info(f"Sending email to {recipient} with subject: {subject}")
        
        message_id = f"email_{self.request.id}"
        
        logger.info(f"Email sent successfully. Message ID: {message_id}")
        
        return {
            "status": "success",
            "message_id": message_id,
            "recipient": recipient,
            "type": "email"
        }
    except Exception as exc:
        logger.error(f"Failed to send email to {recipient}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(
    bind=True,
    base=BaseTask,
    name='app.tasks.send_sms',
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_sms(self, phone_number: str, message: str, **kwargs) -> Dict[str, Any]:

    try:
        logger.info(f"Sending SMS to {phone_number}")

        message_id = f"sms_{self.request.id}"
        
        logger.info(f"SMS sent successfully. Message ID: {message_id}")
        
        return {
            "status": "success",
            "message_id": message_id,
            "phone_number": phone_number,
            "type": "sms"
        }
    except Exception as exc:
        logger.error(f"Failed to send SMS to {phone_number}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(
    bind=True,
    base=BaseTask,
    name='app.tasks.send_push',
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_push(self, device_token: str, title: str, body: str, **kwargs) -> Dict[str, Any]:

    try:
        logger.info(f"Sending push notification to device {device_token[:10]}...")

        message_id = f"push_{self.request.id}"
        
        logger.info(f"Push notification sent successfully. Message ID: {message_id}")
        
        return {
            "status": "success",
            "message_id": message_id,
            "device_token": device_token[:10] + "...",
            "type": "push"
        }
    except Exception as exc:
        logger.error(f"Failed to send push notification: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(
    bind=True,
    base=BaseTask,
    name='app.tasks.send_notification',
    max_retries=3,
    default_retry_delay=60,
)
def send_notification(
    self,
    notification_type: str,
    recipient: str,
    subject: Optional[str] = None,
    message: str = "",
    **kwargs
) -> Dict[str, Any]:

    try:
        if notification_type == 'email':
            return send_email.delay(recipient, subject or "", message, **kwargs).get()
        elif notification_type == 'sms':
            return send_sms.delay(recipient, message, **kwargs).get()
        elif notification_type == 'push':
            return send_push.delay(recipient, subject or "", message, **kwargs).get()
        else:
            raise ValueError(f"Unknown notification type: {notification_type}")
    except Exception as exc:
        logger.error(f"Failed to send {notification_type} notification: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(
    bind=True,
    base=BaseTask,
    name='app.tasks.cleanup_old_notifications',
    max_retries=2,
)
def cleanup_old_notifications(self, days: int = 30) -> Dict[str, Any]:

    try:
        logger.info(f"Cleaning up notifications older than {days} days")

        logger.info("Cleanup completed successfully")
        
        return {
            "status": "success",
            "days": days,
            "cleaned_count": 0 
        }
    except Exception as exc:
        logger.error(f"Failed to cleanup old notifications: {exc}")
        raise self.retry(exc=exc, countdown=300) 
