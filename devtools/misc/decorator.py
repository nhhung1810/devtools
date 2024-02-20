import time
import loguru


def time_benchmark_decorator(msg: str, inward_control: bool = False):
    """Decorator for time benchmarking, example usage like

    Args:
        msg (str): The message before the time benchmark
        inward_control (bool): The flag indicate that whether
            should this decorator read the `is_verbose` or `verbose`
            keyword of the `func` to decide logging. Assume that if
            they kw is not there -> auto-logging

    TODO: add usage example
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
