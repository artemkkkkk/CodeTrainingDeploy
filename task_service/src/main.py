from concurrent import futures

import grpc

from task_service import task_service_pb2_grpc

from database.models import Base
from database.session import engine

from grpc_server.task_service_impl import TaskService
from consumers.results_listener import rabbit_results_listener


def serve():
    Base.metadata.create_all(bind=engine)

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    task_service_pb2_grpc.add_TaskServiceServicer_to_server(
        TaskService(),
        server
    )

    server.add_insecure_port("[::]:50053")

    server.start()
    rabbit_results_listener()

    print("Task Service started on port 50053")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
