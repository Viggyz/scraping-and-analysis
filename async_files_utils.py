import logging
import json
import inspect
from pathlib import Path
import aiofiles
import aiofiles.os

async def make_folder(folder_path: str | Path) -> None:
    folder_path = Path(folder_path)
    if not await aiofiles.os.path.exists(folder_path):
        await aiofiles.os.makedirs(folder_path, exist_ok=True)
        logging.info("%s created successfully", folder_path)
    else:
        logging.info("%s already exists", folder_path)


async def process_and_write(file_path: str | Path, fn, *args, **kwargs) -> None:
    file_path = Path(file_path)
    logging.info("Checking if %s exists...", file_path)

    if not await check_file_exists(file_path):
        logging.info(
            "File not found. Running %s with arguments %s and writing to %s...",
            fn.__name__,
            (args, kwargs),
            file_path,
        )

        # Handles both async and regular sync callback functions
        if inspect.iscoroutinefunction(fn):
            result = await fn(*args, **kwargs)
        else:
            result = fn(*args, **kwargs)

        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(result))
    else:
        logging.info("File found. Skipping creation.")


async def check_file_exists(file_path: str | Path) -> bool:
    logging.info("Checking if %s exists...", file_path)
    return await aiofiles.os.path.exists(file_path)