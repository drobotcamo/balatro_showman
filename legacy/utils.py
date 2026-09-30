"""
Project-wide utilities.

progress() is the canonical way to show a progress bar for any long-running
operation. Import it here rather than tqdm directly so defaults stay consistent
and any future output changes (e.g. logging mode, CI suppression) apply everywhere.
"""

from tqdm import tqdm


def progress(iterable=None, *, desc="", unit="it", total=None, **kwargs):
    """
    Wrap an iterable or use as a context manager with a standard progress bar.

    As an iterable wrapper:
        for frame in progress(frames, desc="Processing", unit="frame"):
            ...

    As a context manager (when total is known but items aren't iterated directly):
        with progress(total=500, desc="Extracting", unit="frame") as bar:
            ...
            bar.update(1)
            bar.set_postfix(key=value)
    """
    return tqdm(iterable, desc=desc, unit=unit, total=total, **kwargs)
