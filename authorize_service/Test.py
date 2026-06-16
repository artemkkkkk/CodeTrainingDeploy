from flask import Flask, request, jsonify
import hashlib
import hmac
import time
import base64
import json

app = Flask(__name__)

users_db = {}

SECRET_KEY = "super_secret_key"

def hash_password(password: str) -> str:
    """Простое хеширование (в проде использовать bcrypt/argon2)"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_token(payload: dict, expires_in: int = 3600) -> str:
    """Создание токена (упрощённый JWT)"""
    header = {"alg": "HS256", "typ": "JWT"}
    payload["exp"] = int(time.time()) + expires_in

    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    signature = hmac.new(
        SECRET_KEY.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{header_b64}.{payload_b64}.{signature}"


def verify_token(token: str) -> dict | None:
    """Проверка токена"""
    try:
        header_b64, payload_b64, signature = token.split(".")

        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return None

        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()))

        if payload.get("exp", 0) < time.time():
            return None

        return payload

    except Exception:
        return None


def get_user_from_token(token: str):
    """Получение пользователя из токена"""
    payload = verify_token(token)
    if not payload:
        return None
    return users_db.get(payload.get("username"))

def make_response(result=None, error=None, id=None):
    """Формирование JSON-RPC ответа"""
    response = {
        "jsonrpc": "2.0",
        "id": id
    }

    if error:
        response["error"] = error
    else:
        response["result"] = result

    return response

def rpc_register(params):
    username = params.get("username")
    password = params.get("password")

    if not username or not password:
        return None, {"code": -32602, "message": "Invalid params"}

    if username in users_db:
        return None, {"code": 400, "message": "User already exists"}

    users_db[username] = {
        "username": username,
        "password": hash_password(password)
    }

    return {"message": "User created"}, None


def rpc_login(params):
    username = params.get("username")
    password = params.get("password")

    user = users_db.get(username)

    if not user or user["password"] != hash_password(password):
        return None, {"code": 401, "message": "Invalid credentials"}

    token = create_token({"username": username})

    return {"access_token": token}, None


def rpc_protected(params):
    token = params.get("token")

    if not token:
        return None, {"code": 401, "message": "Token required"}

    user = get_user_from_token(token)

    if not user:
        return None, {"code": 403, "message": "Invalid or expired token"}

    return {"message": f"Hello, {user['username']}!"}, None

RPC_METHODS = {
    "register": rpc_register,
    "login": rpc_login,
    "protected": rpc_protected,
}

@app.route("/rpc", methods=["POST"])
def rpc_handler():
    """
    Обрабатывает все JSON-RPC запросы
    """
    try:
        data = request.json

        method = data.get("method")
        params = data.get("params", {})
        request_id = data.get("id")

        if method not in RPC_METHODS:
            return jsonify(make_response(
                error={"code": -32601, "message": "Method not found"},
                id=request_id
            ))

        result, error = RPC_METHODS[method](params)

        return jsonify(make_response(
            result=result,
            error=error,
            id=request_id
        ))

    except Exception as e:
        return jsonify(make_response(
            error={"code": -32603, "message": "Internal error", "data": str(e)},
            id=None
        ))

if __name__ == "__main__":
    app.run(debug=True)