import os
import sys

def get_memory_usage_mb():
    """
    Returns current process memory usage in MB.
    Works on Linux (cPanel) and Windows (dev).
    """
    # --- Linux / Unix ---
    if os.name == "posix":
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return round(usage.ru_maxrss / 1024, 2)  # MB
        except Exception:
            return None

    # --- Windows ---
    elif os.name == "nt":
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return round(process.memory_info().rss / (1024 * 1024), 2)
        except Exception:
            return None

    return None
