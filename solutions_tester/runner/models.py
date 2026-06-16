from dataclasses import dataclass


@dataclass
class ExecutionResult:
    """Результат выполнения кода."""
    stdout: str
    stderr: str
    execution_time: float
    return_code: int
    timed_out: bool