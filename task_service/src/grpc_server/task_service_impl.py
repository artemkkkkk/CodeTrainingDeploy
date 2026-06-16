import grpc

from task_service import task_service_pb2
from task_service import task_service_pb2_grpc

from task_service import sso_pb2
from task_service import sso_pb2_grpc

from task_service.src.services.task_repository import (
    create_task,
    get_task_testcases,
    save_solution_result
)

from task_service.src.services.rabbitmq_producer import publish_solution

SSO_SERVICE_URL = "localhost:50052"


def get_user_id_by_token(token):
    channel = grpc.insecure_channel(SSO_SERVICE_URL)
    stub = sso_pb2_grpc.ssoServiceStub(channel)
    req = sso_pb2.TokenValidateRequest(token=token)
    try:
        response = stub.TokenValidate(req)
        user_id = int(response.userId)
        return user_id

    except  grpc.RpcError as e:
        print(f"Token validation error: {e.code()} - {e.details()}")

    finally:
        channel.close()


class TaskService(
    task_service_pb2_grpc.TaskServiceServicer
):

    def CreateTask(self, request, context):

        print("=== CreateTask called ===")

        token = request.token
        id_ = get_user_id_by_token(token)

        task_id = create_task(
            user_id=id_,
            name=request.task_name,
            description=request.description,
            difficult=request.difficult,
            test_cases=request.test_cases,
            tags=request.tags
        )

        print("Task saved with id:", task_id)

        return task_service_pb2.CreateTaskResponse(
            status="OK"
        )

    def SubmitSolution(self, request, context):

        task, testcases = get_task_testcases(
            request.task_name
        )

        if not task:
            return task_service_pb2.SubmitSolutionResponse(
                status="TASK_NOT_FOUND"
            )

        token = request.token
        id_ = get_user_id_by_token(token)

        publish_solution(
            {
                "user_id": id_,
                "task_id": task.id,
                "solution": request.code,
                "test_cases": [
                    {
                        "id": tc.id,
                        "wanted_input": tc.input,
                        "wanted_output": tc.wanted_output,
                        "max_time_ms": tc.max_time_ms
                    }
                    for tc in testcases
                ]
            }
        )

        # save_solution_result(
        #     user_id=id_,
        #     task_id=task.id,
        #     status=False,
        # )

        return task_service_pb2.SubmitSolutionResponse(
            status="QUEUED"
        )
