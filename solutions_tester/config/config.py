import logging


class Config:
    def __init__(self, memory_limit: str, cpu_limit: float, pids_limit: int, tmpfs_size: str,
                 rabbit_user: str, rabbit_password: str, rabbit_host: str, rabbit_port: str,
                 rabbit_queue_get: str, rabbit_queue_send: str, rabbit_max_workers: int) -> None:

        self.memory_limit_mb = memory_limit
        self.cpu_limit = cpu_limit
        self.pids_limit = pids_limit
        self.tmpfs_size = tmpfs_size
        self.rabbit_user = rabbit_user
        self.rabbit_password = rabbit_password
        self.rabbit_host = rabbit_host
        self.rabbit_port = rabbit_port
        self.rabbit_queue_get = rabbit_queue_get
        self.rabbit_queue_send = rabbit_queue_send
        self.rabbit_max_workers = rabbit_max_workers


__instance = None


def load_config() -> None | Config:
    global __instance

    if __instance is not None:
        return __instance
    else:
        import os
        from dotenv import load_dotenv

        exist = load_dotenv()

        if exist:
            logging.info(f"Config loaded successfully")
            return Config(
                memory_limit=os.getenv("MEMORY_LIMIT_MB") + "m",
                cpu_limit=float(os.getenv("CPU_LIMIT")),
                pids_limit=int(os.getenv("PIDS_LIMIT")),
                tmpfs_size=os.getenv("TMPFS_SIZE") + "m",
                rabbit_user=os.getenv("RABBIT_USER"),
                rabbit_password=os.getenv("RABBIT_PASSWORD"),
                rabbit_host=os.getenv("RABBIT_HOST"),
                rabbit_port=os.getenv("RABBIT_PORT"),
                rabbit_queue_get=os.getenv("RABBIT_QUEUE_GET"),
                rabbit_queue_send=os.getenv("RABBIT_QUEUE_SEND"),
                rabbit_max_workers=int(os.getenv("RABBIT_MAX_WORKERS"))
            )

        else:
            logging.error("Failed to load config: needed argument not found")
            return None
