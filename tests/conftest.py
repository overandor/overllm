from __future__ import annotations

import functools
import importlib.util


@functools.lru_cache(maxsize=1)
def tiktoken_encoding_reachable() -> bool:
    """Whether tiktoken is installed AND its encoding data is actually loadable.

    Package presence alone isn't enough: tiktoken fetches encoding vocab files
    from openaipublic.blob.core.windows.net on first use, which this repo's
    sandboxed egress policy blocks (see docs/SEMANTIC_TRANSFORM_FINGERPRINT.md).
    A skip condition that only checks `find_spec("tiktoken")` hard-fails tests
    with a network error instead of skipping in that environment.
    """
    if importlib.util.find_spec("tiktoken") is None:
        return False
    try:
        import tiktoken

        tiktoken.get_encoding("cl100k_base")
    except Exception:
        return False
    return True
