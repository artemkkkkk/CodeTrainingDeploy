import grpc

from task_service import task_service_pb2, task_service_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")

stub = task_service_pb2_grpc.TaskServiceStub(channel)

response = stub.SubmitSolution(
    task_service_pb2.SubmitSolutionRequest(
        token="test",
        task_name="Two Sum",
        code="""
print(sum(map(int, input().split())))
"""
    )
)

print(response.status)
