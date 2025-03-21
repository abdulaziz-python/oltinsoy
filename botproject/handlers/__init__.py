from .user import router as user_router
from .admin import router as admin_router
from .task import router as task_router

__all__ = ['user_router', 'admin_router', 'task_router']

