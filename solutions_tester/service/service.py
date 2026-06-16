import asyncio
import logging
from typing import Callable


class Service:
    def __init__(self, runner_: Callable, cfg):
        self.runner_ = runner_
        self.cfg = cfg

    async def process_message(self, body: dict) -> dict:
        logging.info(f"process_message: {body["user_id"]=}, {body["task_id"]=}")

        res = {
            "user_id": body["user_id"],
            "task_id": body["task_id"],
            "status": True,
            "failed_testcases": []
        }

        tasks = []

        num_of_tests = len(body["test_cases"]) if len(body["test_cases"]) <= 5 else 5

        for idx in range(num_of_tests):
            tasks.append(self.runner_(
                code=body["solution"],
                timeout=body["test_cases"][idx]["max_time_ms"] / 1000.0,
                stdin_data=body["test_cases"][idx]["wanted_input"],
                cfg=self.cfg,
            ))

        testing_results = await asyncio.gather(*tasks)

        for idx, result in enumerate(testing_results):
            if result.stdout != body["test_cases"][idx]["wanted_output"] or result.timed_out or result.stderr != "":
                res["status"] = False
                res["failed_testcases"].append({
                    "id": body["test_cases"][idx]["id"],
                    "wanted_input": body["test_cases"][idx]["wanted_input"],
                    "wanted_output": body["test_cases"][idx]["wanted_output"],
                    "recieved_output": result.stdout + result.stderr,
                    "max_time_ms": body["test_cases"][idx]["max_time_ms"],
                    "recieved_time_ms": str(result.execution_time),
                })

        logging.info(f"process_message ended: {body["user_id"]=}, {body["task_id"]=}")

        return res
