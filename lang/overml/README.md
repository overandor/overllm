# OverML

A small, statically shape-checked, deterministic-by-default language for ML
— compiled to a C-ABI shared library so it can be **imported as a package
from any host language**, plus a standalone toolchain for running it
directly.

```
fn matmul_relu(a: Tensor<f32, [M, N]>, b: Tensor<f32, [N, P]>) -> Tensor<f32, [M, P]> {
    return a @ b;
}

let x: Tensor<f32, [2, 3]> = tensor([[1, 2, 3], [4, 5, 6]]);
let w: Tensor<f32, [3, 2]> = tensor([[1, 0], [0, 1], [1, 1]]);
print(matmul_relu(x, w));   // shape/dtype mismatches are compile errors, not runtime crashes
```

Also includes `KvCache<dtype, [heads, capacity, head_dim]>`, a fixed-capacity
ring buffer for attention caches — `kv_push` evicts the oldest step once full
instead of growing, so a cache's memory is bounded by its type, not by how
long the sequence runs (see `examples/kv_cache_window.oml`).

OverML is also checked, individually, against specific design mistakes from
languages that predate C — implicit typing (FORTRAN), unstructured `GOTO`
control flow (FORTRAN/BASIC/COBOL), dynamic scoping (early Lisp), call-by-name
(ALGOL), silent integer overflow (FORTRAN/B/assembly), and unchecked array
access (FORTRAN/B/assembly) — each with a named source and a passing test.
See [`docs/DESIGN.md`](docs/DESIGN.md#prehistoric-lineage-flaws-inherited-from-pre-c-languages)
for the full table, including one real bug (dynamic scoping) this check
actually found and fixed.

See [`docs/DESIGN.md`](docs/DESIGN.md) for the full language design, type
system, reproducibility model, and packaging format.

## Build

```bash
cargo build --release
```

Produces `target/release/{omlc,omlpkg}` (CLIs) and
`target/release/liboverml.{so,dylib,dll}` (the embeddable library).

## Run a script

```bash
cargo run --bin omlc -- run examples/hello.oml
cargo run --bin omlc -- check examples/tensor_shape_safety.oml   # type-check only
```

## Use a package (multi-file, with dependencies)

```bash
cargo run --bin omlpkg -- run --manifest examples/pkg_demo
```

Scaffold a new one:

```bash
target/release/omlpkg init my_project
cd my_project && ../target/release/omlpkg run
```

## Import it from another language

Build the library, then from Python:

```bash
cargo build --release
cd bindings/python
python3 -c "
import overml
r = overml.eval('print(1 + 1);')
print(r.stdout, r.provenance)
"
```

Any other language follows the same shape: `dlopen`/load
`liboverml.{so,dylib,dll}`, call `overml_eval(source, &stdout, &provenance,
&error) -> int`, free the returned strings with `overml_free_string`. See
`src/lib.rs` for the exact signatures and `bindings/python/overml/__init__.py`
for a full worked example.

## Test

```bash
cargo test
```

## Layout

```
src/            the language: lexer, parser, type checker, interpreter,
                module resolver, package manager, C ABI
src/bin/        omlc (single-file CLI), omlpkg (package manager CLI)
bindings/python/  reference ctypes binding
examples/       runnable .oml programs, including a two-package example
docs/DESIGN.md  full design doc, including current limitations
tests/          integration tests running the examples end to end
```
