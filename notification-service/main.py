import asyncio
import threading
import logging
from flask import Flask, jsonify
from app.celery_app import celery_app
from app.event_consumer import NotificationEventConsumer

app = Flask(__name__)
logger = logging.getLogger(__name__)

consumer: NotificationEventConsumer = None
consumer_thread: threading.Thread = None


def run_consumer():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    global consumer
    consumer = NotificationEventConsumer()
    
    try:
        loop.run_until_complete(consumer.run_forever())
    except Exception as e:
        logger.error(f"Consumer error: {e}", exc_info=True)
    finally:
        loop.close()


def start_consumer():
    global consumer_thread
    
    if consumer_thread is None or not consumer_thread.is_alive():
        consumer_thread = threading.Thread(target=run_consumer, daemon=True)
        consumer_thread.start()
        logger.info("Started notification event consumer in background thread")


start_consumer()


@app.route('/')
def home():
    return {"message": "notification-service"}


@app.route('/health')
def health():
    try:
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        consumer_status = "running" if (consumer_thread and consumer_thread.is_alive()) else "stopped"
        
        return jsonify({
            "status": "healthy",
            "service": "notification-service",
            "celery": {
                "workers": len(active_workers) if active_workers else 0,
                "broker_connected": True
            },
            "event_consumer": {
                "status": consumer_status
            }
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503


if __name__ == '__main__':
    start_consumer()
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5002)