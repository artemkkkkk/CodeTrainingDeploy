import pika
import json
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time


class Consumer:
    def __init__(self, service: object, host: str, port: str, user: str, password: str,
                 queue_get: str, queue_send: str, max_workers: int):

        self._service = service

        self.host = host
        self.port = port

        self.credentials = pika.PlainCredentials(user, password)

        self.queue_get = queue_get
        self.queue_send = queue_send

        self.max_workers = max_workers
        self.connection = None
        self.channel = None
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        self._lock = Lock()
        self._active_tasks = {}
        self._cancelled_tasks = set()
        
        logging.info("Consumer initialized")

    def connect(self, max_retries=30, retry_delay=5):
        for attempt in range(1, max_retries + 1):
            try:
                logging.info(f"Try connect to RabbitMQ ({attempt}/{max_retries})...")

                parameters = pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=self.credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300,
                )
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()

                self.channel.queue_declare(queue=self.queue_get, durable=True)
                self.channel.queue_declare(queue=self.queue_send, durable=True)
                self.channel.basic_qos(prefetch_count=self.max_workers)

                logging.info(f"Connected to RabbitMQ. Queues: {self.queue_get}, {self.queue_send}")
                return

            except pika.exceptions.AMQPConnectionError as e:
                logging.warning(f"Failed to connect: {e}")
                if attempt < max_retries:
                    logging.info(f"Retry to connect in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logging.error(f"Failed to connect after {max_retries} tries")
                    raise

        raise RuntimeError("Failed to connect to RabbitMQ")

    def process_task(self, ch, method, properties, body):
        try:
            data = json.loads(body)
            logging.info(f"Task received: {data}")

            future = self.executor.submit(self._handle_business_logic, data, ch, method, properties)

            with self._lock:
                self._active_tasks[method.delivery_tag] = future

        except json.JSONDecodeError:
            logging.error("Invalid format JSON")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logging.error(f"Error adding task in pool: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def _handle_business_logic(self, data, ch, method, properties):
        try:
            with self._lock:
                if method.delivery_tag in self._cancelled_tasks:
                    logging.info(f"Task {method.delivery_tag} was canceled, skipping execution")
                    return

            to_send = asyncio.run(self._service.process_message(data))

            with self._lock:
                if method.delivery_tag in self._cancelled_tasks:
                    logging.info(f"Task {method.delivery_tag} was canceled during execution, skipping execution")
                    return

                self._safe_publish(to_send, properties)
                self._safe_ack(method.delivery_tag)

                self._active_tasks.pop(method.delivery_tag, None)

            logging.info(f"Task completed: {to_send}")

        except Exception as e:
            logging.error(f"Failed to process task, error: {e}")

            with self._lock:
                if method.delivery_tag in self._cancelled_tasks:
                    logging.info(f"Task {method.delivery_tag} was canceled, skipping nack")
                    return

            self._safe_nack(method.delivery_tag, requeue=False)
            self._active_tasks.pop(method.delivery_tag, None)

    def _safe_publish(self, message, properties):
        def _publish():
            routing_key = self.queue_send

            pub_props = pika.BasicProperties()
            if properties.correlation_id:
                pub_props.correlation_id = properties.correlation_id

            self.channel.basic_publish(
                exchange="",
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pub_props
            )
            logging.info(f"Queue: {routing_key} | Sent message: {message}")

        if self.connection.is_open:
            self.connection.add_callback_threadsafe(_publish)

    def _safe_ack(self, delivery_tag):
        def _ack():
            self.channel.basic_ack(delivery_tag=delivery_tag)

        if self.connection.is_open:
            self.connection.add_callback_threadsafe(_ack)

    def _safe_nack(self, delivery_tag, requeue=False):
        def _nack():
            self.channel.basic_nack(delivery_tag=delivery_tag, requeue=requeue)

        if self.connection.is_open:
            self.connection.add_callback_threadsafe(_nack)

    def start_consuming(self):
        self.connect()

        self.channel.basic_consume(
            queue=self.queue_get,
            on_message_callback=self.process_task
        )

        logging.info("Waiting messages")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.graceful_stop()

    def graceful_stop(self):
        logging.info("Consumer stopping...")
        if self.channel:
            self.channel.stop_consuming()

        with self._lock:
            for delivery_tag, future in list(self._active_tasks.items()):
                if not future.done():
                    self._cancelled_tasks.add(delivery_tag)

                    def _neck_task(dt=delivery_tag):
                        self.channel.basic_nack(delivery_tag=dt, requeue=True)
                        logging.info(f"Task {dt} was cancelled and nacked (requeue=True)")

                    if self.connection and self.connection.is_open:
                        self.connection.add_callback_threadsafe(_neck_task)

        if self.connection and self.connection.is_open:
            self.connection.process_data_events(time_limit=1)

        if self.executor:
            self.executor.shutdown(wait=False)
            logging.info("Executor shutdown (wait=False)")

        if self.connection and self.connection.is_open:
            self.connection.close()

        logging.info("Consumer stopped gracefully")
