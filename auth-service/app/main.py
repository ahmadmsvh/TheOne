from fastapi import FastAPI

from app.api.v1 import api_router

app = FastAPI(
    title="Auth Service",
    description="Authentication and authorization service",
    version="1.0.0"
)

# Include API routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "auth-service"}
