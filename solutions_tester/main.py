import asyncio
import logging
import sys

from runner import cleanup_containers, setup_signal_handlers, run_code_in_docker
from service import Service
from rabbit import Consumer
from config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,
)

CFG = load_config()


async def main() -> None:
    loop = asyncio.get_running_loop()
    setup_signal_handlers(loop)

    try:
        logging.info("===== START =====")

        srvc = Service(runner_=run_code_in_docker, cfg=CFG)
        rabbit = Consumer(
            service=srvc,
            host=CFG.rabbit_host,
            port=CFG.rabbit_port,
            user=CFG.rabbit_user,
            password=CFG.rabbit_password,
            queue_get=CFG.rabbit_queue_get,
            queue_send=CFG.rabbit_queue_send,
            max_workers=CFG.rabbit_max_workers
        )

        rabbit.connect()
        rabbit.start_consuming()

    finally:
        logging.info("===== GRACEFUL SHUTDOWN =====")
        rabbit.graceful_stop()
        await cleanup_containers()
        logging.info("===== APPLICATION CLOSED =====")

if __name__ == "__main__":
    asyncio.run(main())

