import grpc

from task_service import task_service_pb2, task_service_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")

stub = task_service_pb2_grpc.TaskServiceStub(channel)

response = stub.CreateTask(
    task_service_pb2.CreateTaskRequest(
        token="test_token",
        task_name="Two Sum",
        description="Find two numbers",
        difficult="easy",

        tags=[
            "array",
            "two_pointers"
        ],
        test_cases=[
            task_service_pb2.TestCase(
                wanted_input="1 2",
                wanted_output="3",
                max_time_ms=1000
            )
        ]
    )
)

print(response.status)
