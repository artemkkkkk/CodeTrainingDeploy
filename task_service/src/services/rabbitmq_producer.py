import json

import pika


def publish_solution(message: dict):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters("localhost")
    )

    channel = connection.channel()

    channel.queue_declare(
        queue="solutions",
        durable=True
    )

    channel.basic_publish(
        exchange="",
        routing_key="solutions",
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2
        )
    )

    connection.close()
