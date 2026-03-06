import logging
import os
import shutil
import subprocess

from app.constants import COMMAND_TIMEOUT_SECONDS


def run_command(command, timeout=COMMAND_TIMEOUT_SECONDS):
    display = " ".join(os.fspath(part) for part in command)
    logging.info("Running command: %s", display)
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except Exception as exc:
        logging.error("Command execution error: %s", exc)
        return False, None

    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="ignore").strip()
        logging.error("Command failed with code %s: %s", completed.returncode, stderr)
        return False, completed

    return True, completed


def find_first_binary(candidates):
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None
