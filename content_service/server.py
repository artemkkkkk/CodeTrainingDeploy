import grpc
from concurrent import futures

import content_service_pb2
import content_service_pb2_grpc

import sso_pb2
import sso_pb2_grpc

import db_mongo
from db_postgres import Database


SSO_SERVICE_URL = "localhost:50052"

postgres_db = Database()


class ContentService(content_service_pb2_grpc.ContentServiceServicer):

    # ЗАГРУЗКА ЗАДАЧ
    def LoadTasks(self, request, context):
        tasks_data = postgres_db.get_tasks(
            request.offset,
            request.limit,
            request.difficult
        )

        tasks = []

        for task in tasks_data:
            tasks.append(content_service_pb2.Task(
                name=task["name"],
                description=task["description"],
                difficult=task["difficult"],
                complete=task["complete"],
                tried=task["tried"],
                tags=task["tags"]
            ))

        return content_service_pb2.LoadTasksResponse(tasks=tasks)

    # ПРОФИЛЬ
    def LoadProfile(self, request, context):
        # TODO: после интеграции получать user_id из Authorize Service по token
        user_id = 1

        token = request.token

        channel = grpc.insecure_channel(SSO_SERVICE_URL)
        stub = sso_pb2_grpc.ssoServiceStub(channel)
        req = sso_pb2.TokenValidateRequest(token=token)

        try:
            response = stub.TokenValidate(req)
            user_id = int(response.userId)
        except  grpc.RpcError as e:
            print(f"Token validation error: {e.code()} - {e.details()}")

        channel.close()

        profile = postgres_db.get_profile(user_id)

        if not profile:
            return content_service_pb2.LoadProfileResponse()

        return content_service_pb2.LoadProfileResponse(
            name=profile["name"],
            description=profile["description"],
            avatar_url=profile["avatar_url"],
            rating=profile["rating"],
            easy_tasks=profile["easy_tasks"],
            medium_tasks=profile["medium_tasks"],
            hard_tasks=profile["hard_tasks"]
        )

    # КОММЕНТАРИИ
    def LoadComments(self, request, context):
        comments_data = db_mongo.get_comments(
            request.task_name,
            request.offset,
            request.limit
        )

        comments = []

        for comment in comments_data:
            comments.append(content_service_pb2.Comment(
                author_name=comment["author_name"],
                text=comment["text"],
                date=comment["date"]
            ))

        return content_service_pb2.LoadCommentsResponse(comments=comments)

    def LoadSubmissionStatus(self, request, context):
        token = request.token

        channel = grpc.insecure_channel(SSO_SERVICE_URL)
        stub = sso_pb2_grpc.ssoServiceStub(channel)
        req = sso_pb2.TokenValidateRequest(token=token)

        try:
            response = stub.TokenValidate(req)
            user_id = int(response.userId)
        except  grpc.RpcError as e:
            print(f"Token validation error: {e.code()} - {e.details()}")
            return

        channel.close()

        exist, status = postgres_db.get_submission(user_id, request.task_name)

        return content_service_pb2.LoadSubmissionStatusResponse(exist=exist, status=status)


def serve():
    # Создаём таблицы, если их ещё нет
    postgres_db.create_tables()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    content_service_pb2_grpc.add_ContentServiceServicer_to_server(
        ContentService(),
        server
    )

    server.add_insecure_port("[::]:50051")
    server.start()

    print("Content Service запущен на порту 50051")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
    