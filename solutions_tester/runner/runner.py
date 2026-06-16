import asyncio
import logging
import tempfile
import os
import time
import signal
import uuid
from typing import Optional

from .models import ExecutionResult

_active_containers = set()
_lock = asyncio.Lock()


async def cleanup_containers():
    """Принудительно останавливает и удаляет все контейнеры, созданные этим модулем."""
    async with _lock:
        for container_id in list(_active_containers):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", container_id,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except Exception:
                pass

        logging.info("Docker module closed gracefully")
        _active_containers.clear()


def setup_signal_handlers(loop):
    """Регистрирует обработчики сигналов для корректного завершения."""

    async def shutdown(signame):
        logging.info(f"Получен сигнал {signame}. Очищаю контейнеры...")
        await cleanup_containers()
        # Отменяем все активные задачи
        for task in asyncio.all_tasks(loop):
            task.cancel()

    for signame in ('SIGINT', 'SIGTERM'):
        try:
            loop.add_signal_handler(
                getattr(signal, signame),
                lambda s=signame: asyncio.create_task(shutdown(s))
            )
        except (NotImplementedError, RuntimeError):
            # На Windows add_signal_handler не работает
            pass


async def _ensure_image_exists(image: str):
    """Проверяет наличие образа локально и скачивает его, если его нет."""
    proc = await asyncio.create_subprocess_exec(
        "docker", "image", "inspect", image,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )

    if await proc.wait() != 0:
        logging.info(f"[INFO] Образ '{image}' не найден локально. Начинаю загрузку...")
        pull_proc = await asyncio.create_subprocess_exec(
            "docker", "pull", image,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        if await pull_proc.wait() != 0:
            stderr = await pull_proc.stderr.read()
            raise RuntimeError(f"Не удалось загрузить образ '{image}'. Ошибка Docker:\n{stderr.decode('utf-8')}")

        logging.info(f"[INFO] Образ '{image}' успешно загружен.")


async def run_code_in_docker(
        code: str,
        timeout: float,
        stdin_data: str = "",
        image: str = "python:3.10-slim",
        cfg = None,
) -> ExecutionResult | None:
    """
    Асинхронно запускает переданный код в изолированном Docker-контейнере.

    :param code: Строка с исходным кодом для выполнения.
    :param timeout: Максимальное время выполнения в секундах.
    :param stdin_data: Строка, которая будет передана в стандартный ввод (stdin) программы.
    :param image: Docker-образ для запуска (по умолчанию python:3.10-slim).
    :return: Объект ExecutionResult с результатами выполнения.
    """
    if not code.strip():
        raise ValueError("Код для выполнения не может быть пустым")

    await _ensure_image_exists(image)

    container_name = f"sandbox_{uuid.uuid4().hex}"
    async with _lock:
        _active_containers.add(container_name)

    # Создаем временную директорию вместо файла
    temp_dir = tempfile.mkdtemp()
    temp_code_path = os.path.join(temp_dir, "script.py")

    # Записываем код в файл
    with open(temp_code_path, 'w', encoding='utf-8') as f:
        f.write(code)

    try:
        start_time = time.time()

        cmd = [
            "docker", "run", "--rm", "-i",
            "--name", container_name,
            "--network", "none",

            # --- ОГРАНИЧЕНИЕ РЕСУРСОВ ---
            "-m", cfg.memory_limit_mb,
            "--memory-swap", cfg.memory_limit_mb,
            "--cpus", str(cfg.cpu_limit),
            "--pids-limit", str(cfg.pids_limit),

            # --- БЕЗОПАСНОСТЬ ФАЙЛОВОЙ СИСТЕМЫ ---
            "--read-only",
            "--tmpfs", f"/tmp:rw,size={cfg.tmpfs_size},noexec,nosuid,nodev",

            "-v", f"{temp_code_path}:/script.py:ro",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            image,
            "python3", "/script.py"
        ]

        # Создаем асинхронный подпроцесс
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            # Ждем завершения с таймаутом
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=stdin_data.encode('utf-8')),
                timeout=timeout
            )

            execution_time = time.time() - start_time

            return ExecutionResult(
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                execution_time=execution_time,
                return_code=proc.returncode or 0,
                timed_out=False
            )

        except asyncio.TimeoutError:
            # Если время вышло, принудительно убиваем контейнер
            try:
                kill_proc = await asyncio.create_subprocess_exec(
                    "docker", "kill", container_name,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await asyncio.wait_for(kill_proc.wait(), timeout=3.0)
            except Exception:
                pass

            execution_time = time.time() - start_time

            # Пытаемся дочитать то, что успело накопиться
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=1.0)
                stdout_str = stdout.decode('utf-8', errors='replace')
                stderr_str = stderr.decode('utf-8', errors='replace')
            except Exception:
                stdout_str = ""
                stderr_str = ""
                try:
                    proc.kill()
                except Exception:
                    pass

            stderr_str += f"\n[Timeout] Превышен лимит времени выполнения: {timeout} сек."

            return ExecutionResult(
                stdout=stdout_str,
                stderr=stderr_str,
                execution_time=execution_time,
                return_code=-1,
                timed_out=True
            )

    except FileNotFoundError:
        raise RuntimeError("Cant find command 'docker'. Убедитесь, что Docker установлен и доступен в PATH.")

    finally:
        async with _lock:
            _active_containers.discard(container_name)

        # Удаляем временную директорию и файл
        try:
            if os.path.exists(temp_code_path):
                os.remove(temp_code_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except OSError as e:
            logging.warning(f"Failed to delete temp files: {e}")