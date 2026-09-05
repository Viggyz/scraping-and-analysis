import os
import logging
import json
from pathlib import Path


def make_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        logging.info("%s created successfully", folder_path)
    else:
        logging.info("%s already exists", folder_path)


def process_and_write(file_path, fn, *args, **kwargs):
    logging.info("Checking if %s exists...", file_path)
    if not Path(file_path).exists():
        logging.info("File not found. Running %s with arguments %s and writing to %s...",
                     fn.__name__, (args, kwargs), file_path)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(fn(*args, **kwargs), f)
    else:
        logging.info("File found. Skipping creation.")


def check_file_exists(file_path) -> bool:
    logging.info("Checking if %s exists...", file_path)
    if not Path(file_path).exists():
        return False
    else:
        return True
