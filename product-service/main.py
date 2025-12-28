from flask import Flask, jsonify
import os
import asyncio

from app.core.database import get_db_manager
from app.api.v1.products import bp as products_bp
from app.utils import run_async
from app.services.event_consumer import get_event_consumer
from shared.logging_config import setup_logging, get_logger
from shared.config import get_settings

settings = get_settings()
setup_logging(service_name=os.getenv("SERVICE_NAME"), log_level=settings.app.log_level)
logger = get_logger(__name__, os.getenv("SERVICE_NAME"))


def create_app(config=None, init_db=True):

    app = Flask(__name__)
    
    # Load configuration if provided
    if config:
        app.config.update(config)
    
    # Register blueprints
    app.register_blueprint(products_bp)
    
    # Register routes
    @app.route("/")
    def home():
        """Health check endpoint"""
        return jsonify({"message": "product-service-running", "status": "ok"})
    
    @app.route("/health")
    def health_check():
        """Health check with database connection"""
        try:
            db_manager = get_db_manager()
            is_healthy = run_async(db_manager.health_check())
            if is_healthy:
                return jsonify({
                    "status": "healthy",
                    "service": "product-service",
                    "database": "connected"
                }), 200
            else:
                return jsonify({
                    "status": "unhealthy",
                    "service": "product-service",
                    "database": "disconnected"
                }), 503
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                "status": "unhealthy",
                "service": "product-service",
                "error": str(e)
            }), 503
    
    # Initialize database if requested
    if init_db:
        _init_database()
    
    # Start event consumer
    _start_event_consumer()
    
    return app


def _init_database():

    try:
        db_manager = get_db_manager()
        run_async(db_manager.connect())
        run_async(db_manager.create_indexes())
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def _start_event_consumer():
    """Start the event consumer for order events in a background thread"""
    try:
        # Check if RabbitMQ is configured
        if settings.rabbitmq is None:
            logger.warning("RabbitMQ not configured. Event consumer will not start.")
            return
        
        import threading
        
        def run_async_consumer():
            """Run async consumer in a separate event loop"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                event_consumer = get_event_consumer()
                event_consumer.start()
                loop.run_forever()
            except Exception as e:
                logger.error(f"Error in consumer thread: {e}", exc_info=True)
            finally:
                loop.close()
        
        consumer_thread = threading.Thread(target=run_async_consumer, daemon=True)
        consumer_thread.start()
        logger.info("Event consumer thread started successfully")
    except Exception as e:
        logger.error(f"Failed to start event consumer: {e}", exc_info=True)
        # Don't fail app startup if event consumer fails


# Create app instance with automatic database initialization
app = create_app()


if __name__ == "__main__":
    app.run(debug=True, use_reloader=True, host="0.0.0.0", port=5001)
