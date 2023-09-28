import fnmatch
import time
from typing import Any, Dict, Generator, List
from pathlib import Path
import json
import os
import loguru


def is_serializable(x: Any) -> bool:
    """A try-before-ask approach to checking serializable of Object

    Args:
        x (Any): object

    Returns:
        bool: is obj serializable?
    """
    try:
        json.dumps(x)
        return True
    except:
        return False


def make_nest_path(path: str, is_file=True) -> str:
    """Make nest path, return the directory

    Args:
        path (str): The path to the file/directory
        is_file (bool, optional): is this path represent a
            file or a dir. Defaults to True.
    """

    def make_nested_dir(directory: str) -> str:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return directory

    if not is_file:
        return make_nested_dir(path)

    return make_nested_dir(os.path.dirname(path))


def time_benchmark_dec(msg: str, inward_control: bool = False):
    """Decorator for time benchmarking, example usage like

    Args:
        msg (str): The message before the time benchmark
        inward_control (bool): The flag indicate that whether
            should this decorator read the `is_verbose` or `verbose`
            keyword of the `func` to decide logging. Assume that if
            they kw is not there -> auto-logging
    """

    def _wrapper(func):
        def _inner(*args, **kwargs):
            is_logging = (
                True
                if (not inward_control)
                else (kwargs.get("verbose", True) or kwargs.get("is_verbose", True))
            )
            start = time.perf_counter()
            re = func(*args, **kwargs)
            stop = time.perf_counter()
            if is_logging:
                loguru.logger.debug(
                    f"[{msg:<20}] Done analyzed in {stop-start:0.2f} seconds"
                )
            return re

        return _inner

    return _wrapper


def scan_dir(root: str, pattern: str) -> Generator[str]:
    """Scan directory and find file that match pattern

    Args:
        root (str): path of directory to begin scanning
        pattern (str): pattern to filter for

    Yields:
        str: Full path to the file
    """
    for dirpath, _, files in os.walk(root):
        files = fnmatch.filter(files, pattern)
        if len(files) == 0:
            continue
        for filename in files:
            yield os.path.join(dirpath, filename)


def load_json(path: str, encoding: str) -> Any:
    with open(path, mode="r", encoding=encoding) as f:
        return json.load(f)


def write_json(obj: Any, path: str, encoding: str):
    with open(path, mode="w", encoding=encoding) as f:
        json.dump(obj, f)
        pass


def pick(d: Dict[object, object], keys: List[object]):
    return {k: v for k, v in d.items() if k in keys}


def omit(d: Dict[object, object], keys: List[object]):
    return {k: v for k, v in d.items() if k not in keys}
