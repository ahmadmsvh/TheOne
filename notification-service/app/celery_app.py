import os
from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:admin@rabbitmq:5672//")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
SERVICE_NAME = os.getenv("SERVICE_NAME", "notification-service")

celery_app = Celery(
    SERVICE_NAME,
    broker=RABBITMQ_URL,
    backend=f"{REDIS_URL}",
    include=['app.tasks']
)

celery_app.conf.update(
    task_routes={
        'app.tasks.send_email': {'queue': 'notifications.email', 'routing_key': 'notifications.email'},
        'app.tasks.send_sms': {'queue': 'notifications.sms', 'routing_key': 'notifications.sms'},
        'app.tasks.send_push': {'queue': 'notifications.push', 'routing_key': 'notifications.push'},
        'app.tasks.*': {'queue': 'notifications.default', 'routing_key': 'notifications.default'},
    },
    
    task_queues=(
        Queue('notifications.email', 
              exchange=Exchange('notifications', type='topic'),
              routing_key='notifications.email'),
        Queue('notifications.sms',
              exchange=Exchange('notifications', type='topic'),
              routing_key='notifications.sms'),
        Queue('notifications.push',
              exchange=Exchange('notifications', type='topic'),
              routing_key='notifications.push'),
        Queue('notifications.default',
              exchange=Exchange('notifications', type='topic'),
              routing_key='notifications.default'),
    ),
    
    result_backend=f"{REDIS_URL}",
    result_expires=3600,
    result_serializer='json',
    result_compression='gzip',
    
    task_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    
    task_acks_late=True,
    task_reject_on_worker_lost=True,  
    worker_prefetch_multiplier=1,
    
    task_default_retry_delay=60,
    task_max_retries=3,
    task_time_limit=300,
    task_soft_time_limit=240,
    
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    beat_schedule={
        'cleanup-old-notifications': {
            'task': 'app.tasks.cleanup_old_notifications',
            'schedule': crontab(hour=2, minute=0),
        },
    },
    
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    task_ignore_result=False,
    task_store_eager_result=True,
)

celery_app.conf.task_routes.update({
    'app.tasks.send_email': {
        'queue': 'notifications.email',
        'routing_key': 'notifications.email',
        'exchange': 'notifications',
    },
})

celery_app.conf.worker_log_format = (
    '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
)
celery_app.conf.worker_task_log_format = (
    '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'
)
