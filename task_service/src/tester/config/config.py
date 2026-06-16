import logging


logger = logging.getLogger(__name__)

class Config:
    def __init__(self, memory_limit: str, cpu_quota: int, pids_limit: int) -> None:
        self.memory_limit_mb = memory_limit
        self.cpu_quota = cpu_quota
        self.pids_limit = pids_limit


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
            logger.info(f"Config loaded successfully")
            return Config(
                memory_limit=os.getenv("MEMORY_LIMIT_MB") + "m",
                cpu_quota=int(os.getenv("CPU_QUOTA")),
                pids_limit=int(os.getenv("PIDS_LIMIT")),
            )

        else:
            logger.error("Failed to load config: needed argument not found")
            return None
