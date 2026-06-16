class TestResult:
    def __init__(self, success: bool, output: str, used_time: float) -> None:
        self.success = success
        self.output = output
        self.used_time = used_time