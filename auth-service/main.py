import os
from app.main import app
from shared.config import get_settings
from shared.logging_config import setup_logging
from pathlib import Path
from dotenv import load_dotenv

_env_file = Path(__file__) / "shared" / "shared" / ".env"
load_dotenv(dotenv_path=_env_file)

settings = get_settings()

setup_logging(service_name=os.getenv("SERVICE_NAME", "auth-service"), log_level=os.getenv("LOG_LEVEL", "DEBUG"))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)