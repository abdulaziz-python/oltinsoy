import aiohttp
import asyncio
from typing import Dict, Any, Tuple, List, Optional, Union
from datetime import datetime
import json
import hashlib
from contextlib import suppress
import mimetypes
import os
from aiogram import Bot
from config import (
    API_URL,
    API_TIMEOUT,
    API_RETRY_COUNT,
    API_RETRY_DELAY,
    API_POOL_SIZE,
    BOT_TOKEN,
    CACHE_TTL,
    API_BASE_URL
)
from utils.logger import setup_logger
from utils.cache import cache
from functools import wraps
from dataclasses import dataclass

logger = setup_logger(__name__)

def cache_key(func_name: str, *args, **kwargs) -> str:
    key = f"{func_name}:{str(args)}:{str(kwargs)}"
    return hashlib.md5(key.encode()).hexdigest()

def cached(ttl: int = CACHE_TTL):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = cache_key(func.__name__, *args, **kwargs)

            cached_data = cache.get(key)
            if cached_data:
                return cached_data

            result = await func(*args, **kwargs)

            if isinstance(result, APIResponse) and result.success:
                cache.set(key, result, timeout=ttl)
                cache.cleanup()

            return result
        return wrapper
    return decorator

@dataclass
class ApiResponse:
    success: bool
    data: Dict[str, Any] = None
    message: str = None
    status_code: int = 200

class APIResponse:
    def __init__(
        self,
        data: Dict[str, Any],
        status_code: int,
        error: Optional[str] = None
    ):
        self.data = data
        self.status_code = status_code
        self.error = error
        self.success = 200 <= status_code < 300 and not error

    @property
    def message(self) -> str:
        if self.error:
            return self.error
        return self.data.get('message', '')

    def __bool__(self) -> bool:
        return self.success

class APIError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class APIClient:
    _instance = None
    _initialized = False
    _session: Optional[aiohttp.ClientSession] = None
    _bot: Optional[Bot] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not APIClient._initialized:
            self.base_url = API_URL.rstrip('/')
            self.timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
            self.retry_count = API_RETRY_COUNT
            self.retry_delay = API_RETRY_DELAY
            self.logger = setup_logger('api_client')
            APIClient._initialized = True

    async def __aenter__(self):
        await self.ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @classmethod
    async def ensure_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            connector = aiohttp.TCPConnector(
                limit=API_POOL_SIZE,
                ttl_dns_cache=300,
                enable_cleanup_closed=True
            )
            cls._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
            )
        return cls._session

    @classmethod
    async def get_bot(cls) -> Bot:
        if cls._bot is None:
            cls._bot = Bot(token=BOT_TOKEN)
        return cls._bot

    @classmethod
    async def close(cls):
        if cls._session and not cls._session.closed:
            with suppress(Exception):
                await self._session.close()
            cls._session = None
        if cls._bot:
            with suppress(Exception):
                await self._bot.session.close()
            cls._bot = None

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Union[Dict, aiohttp.FormData]] = None,
        params: Optional[Dict] = None,
        files: Optional[List[Dict]] = None
    ) -> APIResponse:
        session = await self.ensure_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {}

        if isinstance(data, dict):
            headers['Content-Type'] = 'application/json'
            data = json.dumps(data)

        try:
            for attempt in range(1, self.retry_count + 1):
                try:
                    async with session.request(
                        method=method,
                        url=url,
                        data=data,
                        params=params,
                        headers=headers,
                        timeout=self.timeout
                    ) as response:
                        try:
                            result = await response.json()
                            return APIResponse(result, response.status)
                        except aiohttp.ContentTypeError:
                            text = await response.text()
                            self.logger.error(f"Invalid JSON response: {text}")
                            raise APIError("Invalid response format", response.status)
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    if attempt == self.retry_count:
                        raise
                    await asyncio.sleep(self.retry_delay * attempt)
        except asyncio.TimeoutError:
            self.logger.error(f"Request timeout for {url}")
            raise APIError("Request timeout", 408)
        except Exception as e:
            self.logger.error(f"Request error: {str(e)}")
            raise APIError(str(e))

    @staticmethod
    def clean_phone_number(phone: str) -> str:
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) == 9:
            return f"998{digits}"
        elif len(digits) == 12 and digits.startswith('998'):
            return digits
        raise ValueError("Invalid phone number format")

    @staticmethod
    def validate_jshir(jshir: str) -> str:
        jshir = jshir.strip()
        if not jshir.isdigit() or len(jshir) != 14:
            raise ValueError("Invalid JSHIR format")
        return jshir

    @cached(ttl=300)
    async def get_user_info(self, telegram_id: int) -> APIResponse:
        return await self._make_request(
            'GET',
            'user-info/',
            params={'telegram_id': telegram_id}
        )

    async def verify_user(
        self,
        phone: str,
        jshir: str,
        telegram_id: int
    ) -> APIResponse:
        try:
            phone = self.clean_phone_number(phone)
            jshir = self.validate_jshir(jshir)

            return await self._make_request(
                'POST',
                'verify-user/',
                {
                    'phone': phone,
                    'jshir': jshir,
                    'telegram_id': telegram_id
                }
            )
        except ValueError as e:
            return APIResponse({'message': str(e)}, 400, str(e))

    @cached(ttl=60)
    async def get_user_tasks(self, telegram_id: int) -> APIResponse:
        return await self._make_request(
            'GET',
            'tasks/',
            params={'telegram_id': telegram_id}
        )

    @cached(ttl=60)
    async def get_task_detail(self, task_id: int) -> APIResponse:
        return await self._make_request('GET', f'tasks/{task_id}/')

    @cached(ttl=60)
    async def get_task_stats(self, task_id: int) -> APIResponse:
        return await self._make_request('GET', f'tasks/{task_id}/stats/')

    async def update_task_status(
        self,
        task_id: int,
        status: str,
        telegram_id: int,
        rejection_reason: Optional[str] = None
    ) -> APIResponse:
        data = {
            'status': status,
            'telegram_id': telegram_id
        }
        if rejection_reason:
            data['rejection_reason'] = rejection_reason

        return await self._make_request(
            'PATCH',
            f'tasks/{task_id}/status/',
            data
        )

    async def submit_task_progress(
        self,
        task_id: int,
        telegram_id: int,
        description: str,
        files: Optional[List[Dict[str, str]]] = None
    ) -> APIResponse:
        """Submit progress for a task with optional files"""
        try:
            # Create form data
            form = aiohttp.FormData()
            form.add_field('task_id', str(task_id))
            form.add_field('telegram_id', str(telegram_id))
            form.add_field('description', description)

            # Add files if provided
            if files:
                for i, file_data in enumerate(files):
                    file_id = file_data.get('file_id')
                    if file_id:
                        file_content = await self.download_telegram_file(file_id)
                        if file_content:
                            form.add_field(
                                f'file_{i}',  # Use indexed field names instead of files[]
                                file_content[0],
                                filename=file_content[1],
                                content_type=file_content[2]
                            )

            # Make the API request
            return await self._make_request('POST', 'submit-progress/', form)
        except Exception as e:
            logger.error(f"Exception in submit_task_progress: {e}")
            return APIResponse(
                {"message": "Topshiriqni yuborishda xatolik yuz berdi"}, 
                500, 
                str(e)
            )

    async def download_telegram_file(
        self,
        file_id: str
    ) -> Optional[Tuple[bytes, str, str]]:
        try:
            bot = await self.get_bot()
            file = await bot.get_file(file_id)
            file_path = file.file_path
            file_name = os.path.basename(file_path)
            content_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'

            file_content = await bot.download_file(file_path)
            return file_content.read(), file_name, content_type
        except Exception as e:
            self.logger.error(f"File download error: {e}")
            return None

    async def grade_task(
        self,
        task_id: int,
        percentage: int,
        status: str,
        admin_id: Optional[int] = None
    ) -> APIResponse:
        """Grade a completed task"""
        data = {
            'task_id': task_id,
            'percentage': percentage,
            'status': status
        }
        
        if admin_id:
            data['admin_id'] = admin_id
        
        return await self._make_request(
            'POST',
            'grade-task/',
            data
        )

    async def get_statistics(self, period: str) -> APIResponse:
        """Get statistics for a specific period (daily, monthly, all)"""
        return await self._make_request(
            'GET',
            f'statistics/{period}/'
        )

    async def send_broadcast(
        self,
        title: str,
        message: str,
        target_type: str,
        target_id: Optional[int] = None,
        admin_id: Optional[int] = None
    ) -> APIResponse:
        """Send broadcast message to users"""
        data = {
            'title': title,
            'message': message,
            'target_type': target_type,
            'admin_id': admin_id
        }
        
        if target_id:
            data['target_id'] = target_id
        
        return await self._make_request(
            'POST',
            'broadcast/',
            data
        )

    async def get_districts(self) -> APIResponse:
        """Get list of districts"""
        return await self._make_request(
            'GET',
            'districts/'
        )

    async def get_mahallas(self) -> APIResponse:
        """Get list of mahallas"""
        return await self._make_request(
            'GET',
            'mahallas/'
        )

async def make_request(method: str, endpoint: str, data: Dict = None, params: Dict = None) -> ApiResponse:
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        async with aiohttp.ClientSession() as session:
            if method.lower() == "get":
                async with session.get(url, params=params) as response:
                    status_code = response.status
                    response_text = await response.text()
                    
                    try:
                        response_data = json.loads(response_text)
                        return ApiResponse(
                            success=True,
                            data=response_data,
                            status_code=status_code
                        )
                    except json.JSONDecodeError:
                        logger.error(f"Invalid response format: {response_text}")
                        return ApiResponse(
                            success=False,
                            message="Invalid response format",
                            status_code=status_code
                        )
            elif method.lower() == "post":
                async with session.post(url, json=data) as response:
                    status_code = response.status
                    response_text = await response.text()
                    
                    try:
                        response_data = json.loads(response_text)
                        if status_code >= 400:
                            return ApiResponse(
                                success=False,
                                message=response_data.get('message', 'Request failed'),
                                status_code=status_code
                            )
                        return ApiResponse(
                            success=True,
                            data=response_data,
                            status_code=status_code
                        )
                    except json.JSONDecodeError:
                        logger.error(f"Invalid response format: {response_text}")
                        return ApiResponse(
                            success=False,
                            message="Invalid response format",
                            status_code=status_code
                        )
    except aiohttp.ClientError as e:
        logger.error(f"Request error: {str(e)}")
        return ApiResponse(
            success=False,
            message=f"Request error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return ApiResponse(
            success=False,
            message=f"Unexpected error: {str(e)}"
        )

api_client = APIClient()

async def verify_user(
    phone: str,
    jshir: str,
    telegram_id: int
) -> APIResponse:
    return await api_client.verify_user(phone, jshir, telegram_id)

async def get_user_info(telegram_id: int) -> APIResponse:
    return await api_client.get_user_info(telegram_id)

async def get_user_tasks(telegram_id: int) -> APIResponse:
    return await api_client.get_user_tasks(telegram_id)

async def get_task_detail(task_id: int) -> APIResponse:
    return await api_client.get_task_detail(task_id)

async def get_task_stats(task_id: int) -> APIResponse:
    return await api_client.get_task_stats(task_id)

async def update_task_status(
    task_id: int,
    status: str,
    telegram_id: int,
    rejection_reason: Optional[str] = None
) -> APIResponse:
    return await api_client.update_task_status(
        task_id,
        status,
        telegram_id,
        rejection_reason
    )

async def submit_task_progress(
    task_id: int,
    telegram_id: int,
    description: str,
    files: Optional[List[Dict[str, str]]] = None
) -> APIResponse:
    return await api_client.submit_task_progress(
        task_id,
        telegram_id,
        description,
        files
    )

async def download_telegram_file(
    file_id: str
) -> Optional[Tuple[bytes, str, str]]:
    return await api_client.download_telegram_file(file_id)

async def get_statistics(period: str) -> APIResponse:
    return await api_client.get_statistics(period)

async def grade_task(
    task_id: int,
    percentage: int,
    status: str,
    admin_id: Optional[int] = None
) -> APIResponse:
    return await api_client.grade_task(task_id, percentage, status, admin_id)

async def get_bot() -> Bot:
    return await api_client.get_bot()

async def send_broadcast(
    title: str,
    message: str,
    target_type: str,
    target_id: Optional[int] = None,
    admin_id: Optional[int] = None
) -> APIResponse:
    return await api_client.send_broadcast(title, message, target_type, target_id, admin_id)

async def get_districts() -> APIResponse:
  """Get list of districts"""
  try:
      async with aiohttp.ClientSession() as session:
          async with session.get(f"{API_URL}/districts/") as response:
              if response.status == 200:
                  districts = await response.json()
                  return APIResponse(districts, response.status)
              else:
                  return APIResponse({}, response.status, "Failed to get districts")
  except Exception as e:
      logger.error(f"Error in get_districts: {e}")
      return APIResponse({}, 500, str(e))

async def get_mahallas() -> APIResponse:
  """Get list of mahallas"""
  try:
      async with aiohttp.ClientSession() as session:
          async with session.get(f"{API_URL}/mahallas/") as response:
              if response.status == 200:
                  mahallas = await response.json()
                  return APIResponse(mahallas, response.status)
              else:
                  return APIResponse({}, response.status, "Failed to get mahallas")
  except Exception as e:
      logger.error(f"Error in get_mahallas: {e}")
      return APIResponse({}, 500, str(e))

async def get_statistics(period: str) -> ApiResponse:
    return await make_request("get", f"statistics/{period}/")

async def get_tasks(user_id: Optional[int] = None, mahalla_id: Optional[int] = None, 
                   district_id: Optional[int] = None, status: Optional[str] = None) -> ApiResponse:
    params = {}
    if user_id:
        params['user_id'] = user_id
    if mahalla_id:
        params['mahalla_id'] = mahalla_id
    if district_id:
        params['district_id'] = district_id
    if status:
        params['status'] = status
    
    return await make_request("get", "tasks/", params=params)

async def get_task_detail(task_id: int) -> ApiResponse:
    return await make_request("get", f"tasks/{task_id}/")

async def grade_task(task_id: int, percentage: int, status: str, admin_id: Optional[int] = None) -> ApiResponse:
    data = {
        "task_id": task_id,
        "percentage": percentage,
        "status": status
    }
    
    if admin_id:
        data["admin_id"] = admin_id
    
    return await make_request("post", "grade-task/", data=data)

