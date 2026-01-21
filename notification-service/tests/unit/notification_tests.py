import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies import require_auth, require_role, require_any_role


class notification_tests:
    
    @pytest.mark.asyncio
    async def test_notification(self):
        
        assert True is not None
    
