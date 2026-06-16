from src.tester.config.config import load_config

cfg = load_config()

print(cfg.memory_limit_mb)
print(cfg.cpu_quota)
print(cfg.pids_limit)
