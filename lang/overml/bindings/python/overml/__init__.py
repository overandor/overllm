"""Python binding for OverML, via ctypes over the C-ABI `liboverml` shared
library — no Python-specific glue was needed inside the Rust crate itself,
which is the point: any language with an FFI story can bind to OverML the
same way this file does.

    import overml
    result = overml.eval('''
        seed(42);
        let x: Tensor<f32, [2, 2]> = tensor([[1, 2], [3, 4]]);
        print(x @ x);
    ''')
    print(result.stdout)
    print(result.provenance)

Build the shared library first (from lang/overml/):

    cargo build --release

`overml.eval` raises `OverMlError` on a lex/parse/type/runtime error, with
the interpreter's own diagnostic message (including file:line:col when
available) as the exception text.
"""

from __future__ import annotations

import ctypes
import os
import platform
import sysconfig
from dataclasses import dataclass
from pathlib import Path


class OverMlError(RuntimeError):
    """Raised when OverML source fails to lex, parse, type-check, or run."""


@dataclass(frozen=True)
class EvalResult:
    stdout: str
    provenance: str


def _library_filename() -> str:
    system = platform.system()
    if system == "Darwin":
        return "liboverml.dylib"
    if system == "Windows":
        return "overml.dll"
    return "liboverml.so"


def _candidate_paths() -> list[Path]:
    here = Path(__file__).resolve().parent
    crate_root = here.parent.parent.parent  # bindings/python/overml -> lang/overml
    name = _library_filename()
    candidates = [
        here / name,  # allow bundling the library alongside the package
        crate_root / "target" / "release" / name,
        crate_root / "target" / "debug" / name,
    ]
    env_override = os.environ.get("OVERML_LIBRARY_PATH")
    if env_override:
        candidates.insert(0, Path(env_override))
    return candidates


def _load_library() -> ctypes.CDLL:
    for path in _candidate_paths():
        if path.is_file():
            return ctypes.CDLL(str(path))
    tried = "\n".join(f"  - {p}" for p in _candidate_paths())
    raise OverMlError(
        "could not find the OverML shared library. Build it with "
        "`cargo build --release` inside lang/overml/, or set "
        f"OVERML_LIBRARY_PATH. Looked in:\n{tried}"
    )


_lib = _load_library()

_lib.overml_eval.argtypes = [
    ctypes.c_char_p,
    ctypes.POINTER(ctypes.c_char_p),
    ctypes.POINTER(ctypes.c_char_p),
    ctypes.POINTER(ctypes.c_char_p),
]
_lib.overml_eval.restype = ctypes.c_int
_lib.overml_free_string.argtypes = [ctypes.c_char_p]
_lib.overml_free_string.restype = None

# silence unused-import warning on some linters; sysconfig kept for future
# platform-tag-based library resolution.
_ = sysconfig


def eval(source: str) -> EvalResult:  # noqa: A001 - mirrors the Rust fn name deliberately
    """Lex, parse, type-check, and run OverML `source`.

    Note: `import` statements are not resolvable through this entry point
    (there's no filesystem context) — run multi-file/package programs via
    the `omlc`/`omlpkg` CLIs instead, e.g. with `subprocess`.
    """
    out_stdout = ctypes.c_char_p()
    out_prov = ctypes.c_char_p()
    out_err = ctypes.c_char_p()

    rc = _lib.overml_eval(
        source.encode("utf-8"),
        ctypes.byref(out_stdout),
        ctypes.byref(out_prov),
        ctypes.byref(out_err),
    )

    try:
        if rc == 0:
            stdout = out_stdout.value.decode("utf-8") if out_stdout.value else ""
            prov = out_prov.value.decode("utf-8") if out_prov.value else ""
            return EvalResult(stdout=stdout, provenance=prov)
        message = out_err.value.decode("utf-8") if out_err.value else "unknown OverML error"
        raise OverMlError(message)
    finally:
        for ptr in (out_stdout, out_prov, out_err):
            if ptr.value is not None:
                _lib.overml_free_string(ptr)
