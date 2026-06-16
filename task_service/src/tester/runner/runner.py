import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import logging
import docker

from tester.config.config import load_config

from .models import *


logger = logging.getLogger(__name__)

CFG = load_config()


def run_user_code(code: str, input_data: str, timeout: int) -> TestResult | None:
    client = docker.from_env()

    container = None

    start_time = time.time()

    try:
        container = client.containers.run(
            image="python:3.9-slim",
            command=["sleep", "infinity"],
            detach=True,
            network_disabled=True,
            mem_limit=CFG.memory_limit_mb,
            cpu_quota=CFG.cpu_quota,
            pids_limit=CFG.pids_limit,
            read_only=True,
            tmpfs={"/tmp": ""},
            security_opt=["no-new-privileges:true"],
        )

        import base64
        code_b64 = base64.b64encode(code.encode()).decode()
        input_b64 = base64.b64encode(input_data.encode()).decode() if input_data else ""

        exec_result = container.exec_run(
            ["sh", "-c", f"echo '{code_b64}' | base64 -d > /tmp/code.py"]
        )
        if exec_result.exit_code != 0:
            logger.error(f"Error during execution code - {exec_result.output}")

        exec_result = container.exec_run(
            ["sh", "-c", f"echo '{input_b64}' | base64 -d > /tmp/input.txt"]
        )
        if exec_result.exit_code != 0:
            logger.error(f"Error during execution input - {exec_result.output}")

        start_time = time.time()

        def execute_in_container():
            return container.exec_run(
                ["sh", "-c", "python /tmp/code.py < /tmp/input.txt"],
                demux=True
            )

        exec_result = None

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(execute_in_container)
            try:
                exec_result = future.result(timeout=timeout)
            except FuturesTimeoutError:
                try:
                    container.kill(signal="SIGKILL")
                except:
                    pass

                try:
                    exec_result = future.result(timeout=5)
                except:
                    pass

                end_time = time.time()
                return TestResult(
                    success=False,
                    output="Time Limit Exceeded",
                    used_time=round(end_time - start_time, 4)
                )

        end_time = time.time()
        execution_time = round(end_time - start_time, 4)

        stdout = exec_result.output[0].decode("utf-8", errors="replace") if exec_result.output[0] else ""
        stderr = exec_result.output[1].decode("utf-8", errors="replace") if exec_result.output[1] else ""

        status = exec_result.exit_code == 0
        logs = stdout + stderr

        logger.info(f"Solution solved successfully: {execution_time}")

        return TestResult(
            success=status,
            output=logs,
            used_time=execution_time,
        )

    except docker.errors.APIError as e:
        end_time = time.time()
        execution_time = round(end_time - start_time, 4)

        logger.error(f"Docker API error - {e}")

        return TestResult(
            success=False,
            output="Internal error",
            used_time=execution_time,
        )

    except Exception as e:
        end_time = time.time()
        execution_time = round(end_time - start_time, 4)

        logger.error(f"Execution Error: {e}")

        return TestResult(
            success=False,
            output="Internal error",
            used_time=execution_time,
        )


    finally:
        if container:
            try:
                container.remove(force=True)

            except Exception as e:
                logger.error(f"Could not remove container: {e}")
