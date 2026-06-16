import os
import time
from concurrent import futures

import bcrypt
import grpc
import jwt
from dotenv import load_dotenv

import sso_pb2
import sso_pb2_grpc

from db_postgres import Database


load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_LIFETIME_SECONDS = int(os.getenv("JWT_LIFETIME_SECONDS", "36000"))

database = Database()


def hash_password(password):
    password_bytes = password.encode("utf-8")
    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed_password.decode("utf-8")


def check_password(password, password_hash):
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )


def create_token(user_id, name):
    payload = {
        "user_id": user_id,
        "name": name,
        "exp": int(time.time()) + JWT_LIFETIME_SECONDS
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm="HS256"
    )


def decode_token(token):
    if isinstance(token, bytes):
        token = token.decode('utf-8')

    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        print("TOKEN ISTEK")
        return None
    except jwt.InvalidTokenError as e:
        print("INVALID TOKEN -", e)
        return None
    except Exception as e:
        print(f"Неожиданная ошибка: {type(e).__name__}: {e}")
        return None

class SsoService(sso_pb2_grpc.ssoServiceServicer):

    def Register(self, request, context):
        if not request.name or not request.email or not request.password:
            return sso_pb2.RegisterResponse(
                status="Ошибка: заполнены не все поля"
            )

        old_user = database.get_user_by_name(request.name)

        if old_user:
            return sso_pb2.RegisterResponse(
                status="Ошибка: пользователь уже существует"
            )

        password_hash = hash_password(request.password)

        database.create_user(
            request.name,
            request.email,
            password_hash
        )

        return sso_pb2.RegisterResponse(
            status="Пользователь успешно зарегистрирован"
        )

    def Login(self, request, context):
        user = database.get_user_by_name(request.name)

        if not user:
            return sso_pb2.LoginResponse(
                status="Ошибка: пользователь не найден",
                token=""
            )

        if not check_password(request.password, user["password_hash"]):
            return sso_pb2.LoginResponse(
                status="Ошибка: неверный пароль",
                token=""
            )

        token = create_token(user["id"], user["name"])

        return sso_pb2.LoginResponse(
            status="Успешный вход",
            token=token
        )

    def TokenValidate(self, request, context):
        payload = decode_token(request.token)

        if not payload:
            return sso_pb2.TokenValidateResponse(
                isValid=False
            )

        user = database.get_user_by_id(payload["user_id"])

        if not user:
            return sso_pb2.TokenValidateResponse(
                isValid=False
            )

        return sso_pb2.TokenValidateResponse(
            isValid=True,
            isModer=user["is_moder"],
            userId=user["id"],
            name=user["name"],
            created_at=user["created_at"]
        )


def serve():
    database.connect()
    database.create_tables()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    sso_pb2_grpc.add_ssoServiceServicer_to_server(
        SsoService(),
        server
    )

    server.add_insecure_port("[::]:50052")
    server.start()

    print("Authorize Service запущен на порту 50052")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
