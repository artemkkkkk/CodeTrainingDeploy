# api_gateway/APIGateway.py
import yaml
import grpc
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

# gRPC-клиенты
import sso_pb2
import sso_pb2_grpc
import task_service_pb2
import task_service_pb2_grpc
import content_service_pb2
import content_service_pb2_grpc

# Загрузка openapi.yaml
with open("api/openapi.yaml", "r", encoding="utf-8") as f:
    OPENAPI_SPEC = yaml.safe_load(f)

CONTENT_SERVICE_URL = "localhost:50051"
SSO_SERVICE_URL = "localhost:50052"
TASK_SERVICE_URL = "localhost:50053"

# Приложение FastAPI
app = FastAPI(
    title="Code Training API Gateway",
    docs_url=None,
    redoc_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic модели для валидации
class DifficultyEnum(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    name: str
    password: str

class LoginResponse(BaseModel):
    status: str
    token: str

class StatusResponse(BaseModel):
    status: str

class Task(BaseModel):
    name: str
    description: str
    difficult: str
    complete: int
    tried: int
    tags: List[str]

class LoadTasksResponse(BaseModel):
    tasks: List[Task]

class LoadProfileRequest(BaseModel):
    authorization: str

class LoadProfileResponse(BaseModel):
    name: str
    description: str = ""
    avatar_url: str = ""
    rating: int
    easy_tasks: int
    medium_tasks: int
    hard_tasks: int

class Comment(BaseModel):
    author_name: str
    text: str
    date: str

class LoadCommentsResponse(BaseModel):
    comments: List[Comment]

class TestCase(BaseModel):
    wanted_input: str
    wanted_output: str
    max_time_ms: int

class CreateTaskRequest(BaseModel):
    task_name: str
    description: str
    difficult: str
    tags: List[str]
    test_cases: List[TestCase]

class SubmitSolutionRequest(BaseModel):
    task_name: str
    code: str

class SubmissionStatusRequest(BaseModel):
    task_name: str

class SubmissionStatusResponse(BaseModel):
    exist: bool
    status: bool

# Вспомогательные функции для gRPC вызовов
def get_token_from_request(authorization: Optional[str] = None) -> str:
    """Извлекает токен из заголовка Authorization: Bearer <token>"""
    if not authorization:
        return ""
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return ""

# Auth endpoints -> sso service
@app.post("/api/v1/auth/register", response_model=StatusResponse)
async def register(request: RegisterRequest):
    """Регистрация нового пользователя → SSO Service.Register"""
    try:
        async with grpc.aio.insecure_channel(SSO_SERVICE_URL) as channel:
            stub = sso_pb2_grpc.ssoServiceStub(channel)
            grpc_request = sso_pb2.RegisterRequest(
                name=request.name,
                email=request.email,
                password=request.password
            )
            response = await stub.Register(grpc_request)
            return StatusResponse(status=response.status)
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC error: {e.code()} - {e.details()}")

@app.post("/api/v1/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Логин пользователя → SSO Service.Login"""
    try:
        async with grpc.aio.insecure_channel(SSO_SERVICE_URL) as channel:
            stub = sso_pb2_grpc.ssoServiceStub(channel)
            grpc_request = sso_pb2.LoginRequest(
                name=request.name,
                password=request.password
            )
            response = await stub.Login(grpc_request)
            return LoginResponse(status=response.status, token=response.token)
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC error: {e.code()} - {e.details()}")

# Content endpoints -> content service
@app.get("/api/v1/tasks", response_model=LoadTasksResponse)
async def get_tasks(
    offset: int = 0,
    limit: int = 10,
    difficult: Optional[DifficultyEnum] = None,
    tags: Optional[List[str]] = None,
    authorization: Optional[str] = None
):
    """Получение списка задач → Content Service.LoadTasks"""
    token = authorization
    try:
        async with grpc.aio.insecure_channel(CONTENT_SERVICE_URL) as channel:
            stub = content_service_pb2_grpc.ContentServiceStub(channel)
            grpc_request = content_service_pb2.LoadTasksRequest(
                token=token,
                offset=offset,
                limit=limit,
                difficult=difficult.value if difficult else "",
                tags=tags or []
            )
            response = await stub.LoadTasks(grpc_request)
            tasks = [
                Task(
                    name=t.name,
                    description=t.description,
                    difficult=t.difficult,
                    complete=t.complete,
                    tried=t.tried,
                    tags=list(t.tags)
                )
                for t in response.tasks
            ]
            return LoadTasksResponse(tasks=tasks)
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC error: {e.code()} - {e.details()}")

@app.get("/api/v1/profile", response_model=LoadProfileResponse)
async def get_profile(authorization: Optional[str] = None):
    """Получение профиля → Content Service.LoadProfile"""
    token = authorization
    try:
        async with grpc.aio.insecure_channel(CONTENT_SERVICE_URL) as channel:
            stub = content_service_pb2_grpc.ContentServiceStub(channel)
            grpc_request = content_service_pb2.LoadProfileRequest(token=token)
            response = await stub.LoadProfile(grpc_request)
            return LoadProfileResponse(
                name=response.name,
                description=response.description,
                avatar_url=response.avatar_url,
                rating=response.rating,
                easy_tasks=response.easy_tasks,
                medium_tasks=response.medium_tasks,
                hard_tasks=response.hard_tasks
            )
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC error: {e.code()} - {e.details()}")

@app.get("/api/v1/tasks/{task_name}/comments", response_model=LoadCommentsResponse)
async def get_comments(
    task_name: str,
    offset: int = 0,
    limit: int = 10,
    authorization: Optional[str] = None
):
    """Получение комментариев → Content Service.LoadComments"""
    token = authorization
    try:
        async with grpc.aio.insecure_channel(CONTENT_SERVICE_URL) as channel:
            stub = content_service_pb2_grpc.ContentServiceStub(channel)
            grpc_request = content_service_pb2.LoadCommentsRequest(
                token=token,
                task_name=task_name,
                offset=offset,
                limit=limit
            )
            response = await stub.LoadComments(grpc_request)
            comments = [
                Comment(
                    author_name=c.author_name,
                    text=c.text,
                    date=c.date
                )
                for c in response.comments
            ]
            return LoadCommentsResponse(comments=comments)
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC error: {e.code()} - {e.details()}")

# Task management endpoints -> Task service
@app.post("/api/v1/tasks", response_model=StatusResponse)
async def create_task(
    request: CreateTaskRequest,
    authorization: Optional[str] = None
):
    """Создание задачи → Task Service.CreateTask"""
    token = authorization

    print(f"DEBUG PRINT {request}")

    try:
        async with grpc.aio.insecure_channel(TASK_SERVICE_URL) as channel:
            stub = task_service_pb2_grpc.TaskServiceStub(channel)
            grpc_request = task_service_pb2.CreateTaskRequest(
                token=token,
                task_name=request.task_name,
                description=request.description,
                difficult=request.difficult,
                tags=request.tags,
                test_cases=[
                    task_service_pb2.TestCase(
                        wanted_input=tc.wanted_input,
                        wanted_output=tc.wanted_output,
                        max_time_ms=tc.max_time_ms
                    )
                    for tc in request.test_cases
                ]
            )
            response = await stub.CreateTask(grpc_request)
            return StatusResponse(status=response.status)
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC error: {e.code()} - {e.details()}")

@app.post("/api/v1/submissions", response_model=StatusResponse)
async def submit_solution(
    request: SubmitSolutionRequest,
    authorization: Optional[str] = None
):
    """Отправка решения → Task Service.SubmitSolution"""
    token = authorization

    print(f"DEBUG PRINT {request.code=}")

    try:
        async with grpc.aio.insecure_channel(TASK_SERVICE_URL) as channel:
            stub = task_service_pb2_grpc.TaskServiceStub(channel)
            grpc_request = task_service_pb2.SubmitSolutionRequest(
                token=token,
                task_name=request.task_name,
                code=request.code
            )
            response = await stub.SubmitSolution(grpc_request)
            return StatusResponse(status=response.status)
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC error: {e.code()} - {e.details()}")

@app.post("/api/v1/submissions/result", response_model=SubmissionStatusResponse)
async def get_submission_status(request: SubmissionStatusRequest, authorization: Optional[str] = None):
    try:
        async with grpc.aio.insecure_channel(CONTENT_SERVICE_URL) as channel:
            stub = content_service_pb2_grpc.ContentServiceStub(channel)
            grpc_request = content_service_pb2.LoadSubmissionStatusRequest(
                token=authorization,
                task_name=request.task_name,
            )
            response = await stub.LoadSubmissionStatus(grpc_request)
            return SubmissionStatusResponse(
                exist=response.exist,
                status=response.status,
            )

    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC error: {e.code()} - {e.details()}")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "api-gateway"}

@app.get("/openapi.json")
async def get_open_api():
    return OPENAPI_SPEC

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Code Training API Gateway"
    )

# Запуск
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("APIGateway:app", host="0.0.0.0", port=8000, reload=True)