import json
from datetime import datetime, timezone

import pika

from task_service.src.services.task_repository import save_solution_result, update_solved_count


def callback(ch, method, properties, body):
    data = json.loads(body)

    print(f"RESULT RECEIVED: {data=}")

    save_solution_result(
        user_id=data["user_id"],
        task_id=data["task_id"],
        status=data["status"],
        solved_at=datetime.now(timezone.utc),
    )

    update_solved_count(
        user_id=data["user_id"],
        task_id=data["task_id"],
    )

    ch.basic_ack(
        delivery_tag=method.delivery_tag
    )


def rabbit_results_listener():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters("localhost")
    )

    channel = connection.channel()

    channel.queue_declare(
        queue="results",
        durable=True
    )

    channel.basic_consume(
        queue="results",
        on_message_callback=callback
    )

    print("Waiting for results...")

    channel.start_consuming()
