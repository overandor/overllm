# OverML Design (v0.1)

OverML is a small language for ML work, built to be *imported* into other
languages rather than to replace them: it compiles to a C-ABI shared library
(`liboverml.so`/`.dylib`/`.dll`) that any host language with an FFI story —
Python, Node, Go, C++, Rust, whatever — can load and call into, the same way
you'd import a native extension. There's also a standalone toolchain
(`omlc`, the single-file compiler/runner, and `omlpkg`, the package manager)
for running OverML programs directly.

This document covers the language as it exists today. It is a real,
type-checked, running implementation, not a spec for something unbuilt — see
"Honest limitations" at the bottom for what's deliberately out of scope for
v0.1.

## Why another language

Three specific, well-known ML-tooling pain points motivated the design:

1. **Weak type safety around tensors.** In most ML stacks, a shape or dtype
   mismatch (`(2, 3) @ (4, 5)`, `float32` vs `float64`) is a runtime
   exception, often hours into a training run. OverML's tensor type carries
   its dtype *and* shape (`Tensor<f32, [2, 3]>`), and shape/dtype agreement
   for every tensor operation is checked statically — see "Type system"
   below.
2. **Fragmented packaging / dependency hell.** `pip` + `conda` +
   CUDA-toolkit version matrices are a well-worn complaint. OverML's package
   manifest (`oml.toml`) is a deliberately tiny format, dependencies are
   pinned by content hash (not just a version string) in `oml.lock`, and the
   whole toolchain has effectively zero external dependencies itself.
3. **Poor reproducibility / determinism.** "Same seed, different numbers" is
   a routine occurrence across numpy versions, BLAS backends, and platforms.
   OverML's random number generator is a from-scratch, pure-integer
   splitmix64 implementation with no OS entropy involved, and every run can
   produce a provenance fingerprint (`provenance_hash()`) that two runs will
   only share if they were observationally identical.

## Language tour

```
// examples/tensor_shape_safety.oml
fn matmul_relu(a: Tensor<f32, [M, N]>, b: Tensor<f32, [N, P]>) -> Tensor<f32, [M, P]> {
    let raw = a @ b;
    return raw;
}

let x: Tensor<f32, [2, 3]> = tensor([[1, 2, 3], [4, 5, 6]]);
let w: Tensor<f32, [3, 2]> = tensor([[1, 0], [0, 1], [1, 1]]);
let y = matmul_relu(x, w);
print(y);
```

Scalar types: `i64`, `f64`, `bool`, `str`. Tensor types: `Tensor<dtype, [dims...]>`
where `dtype` is `f32 | f64 | i32 | i64 | bool` and each dim is an integer
literal or a symbolic name (only meaningful in a function signature).

Statements: `let`, assignment (`x = expr;`), `if`/`else`, `while`, `return`,
`print(...)`, `import mod;`, and function declarations (`fn name(params) ->
Type { ... }`).

Expressions: the usual arithmetic/comparison/boolean operators, plus `@` for
matrix multiplication, `tensor([...])` literals (arbitrary nesting depth,
shape inferred from the literal and validated for raggedness), and indexing
(`t[i]`, rank-1 tensors only in v0.1).

Builtins: `seed(n)`, `zeros(dtype, dims...)`, `ones(dtype, dims...)`,
`rand_tensor(dtype, dims...)`, `provenance_hash()`.

## Type system

The checker (`src/typecheck.rs`) runs a single pass over the AST before any
code executes:

- **Elementwise ops** (`+ - * /`) require identical dtype and identical rank
  + dims on both sides — no broadcasting in v0.1 (a deliberate simplicity
  choice; see limitations).
- **Matmul** (`@`) requires both operands to be rank-2, same dtype, and the
  inner dimensions to unify.
- **Numeric mixing** (`i64` vs `f64`) in an arithmetic op is a type error —
  no implicit coercion, so a silent precision bug can't hide in a spot where
  Python or NumPy would just quietly upcast.
- **Generic functions** declare symbolic dims (`Tensor<f32, [M, N]>`). At
  each call site, the checker binds each symbol to the concrete dimension of
  the first argument that uses it, then requires every subsequent use of
  that symbol — including in the return type — to agree. A return-type
  symbol that no parameter ever bound is a compile error ("return dimension
  'X' is not determined by any parameter"), which catches an unsound
  generic signature before it's ever called.
- **Top-level `let` bindings must have fully concrete shapes** — symbolic
  dims are only meaningful inside a function body where a call site will
  resolve them. Intermediate `let`s *inside* a generic function are allowed
  to stay symbolic (see `tests/examples.rs` and `typecheck.rs` for the
  `in_fn` distinction).

## Reproducibility

`src/rng.rs` implements splitmix64 from scratch: pure 64-bit integer
arithmetic, no OS randomness, no per-platform float rounding differences.
`seed(n)` reseeds the interpreter's generator; `rand_tensor(...)` draws from
it. Two runs of the same program with the same seed produce bit-identical
output, on any machine, forever (there's a regression test for this:
`tests/examples.rs::reproducible_training_is_deterministic_across_two_runs`).

Every `print(...)` and every `rand_tensor` draw is also fed into a running
FNV-1a hash (`provenance_hash()`), so a program can emit a short fingerprint
of its own observable execution — useful for verifying two runs (maybe on
different machines, maybe months apart) were truly identical without diffing
raw output by hand.

## Packaging

`oml.toml` is a deliberately tiny manifest format (hand-parsed, not a full
TOML parser — see `src/pkg.rs`):

```toml
[package]
name = "my_model"
version = "0.1.0"
entry = "main.oml"

[dependencies]
linalg = "../linalg"
```

A dependency is a directory containing a `lib.oml`, whose top-level function
declarations become importable as `modname::fn_name` after `import modname;`
in the importing file. `omlpkg build` resolves every dependency, type-checks
the whole program, and writes `oml.lock`, pinning each dependency by an
FNV-1a content hash of its `lib.oml` — not just a version string, so a build
is reproducible even if a dependency's tag gets force-pushed out from under
you.

```
omlpkg init my_project      # scaffold oml.toml + main.oml
omlpkg build                # resolve deps, type-check, write oml.lock
omlpkg run                  # build, then interpret the entry file
```

## Embedding (the "package any language can import" part)

`src/lib.rs` exposes a small C ABI:

```c
int overml_eval(const char *source,
                 char **out_stdout,
                 char **out_provenance,
                 char **out_error);
void overml_free_string(char *ptr);
```

`overml_eval` lexes, parses, type-checks, and runs `source` with no
filesystem access (so `import` isn't resolvable through this entry point —
run multi-file programs via `omlc`/`omlpkg` instead, e.g. by shelling out).
On success it returns 0 and sets `*out_stdout`/`*out_provenance`; on failure
it returns 1 and sets `*out_error`. Every string it allocates must be freed
with `overml_free_string`.

`bindings/python/overml/` is a ~100-line reference binding built entirely on
`ctypes` against that ABI — no Rust-Python-specific glue (no PyO3) was
needed, which is the point: the same handful of `dlopen`/`ctypes.CDLL`-style
calls work from Node's `ffi-napi`, Go's `cgo`, or C++ directly.

## Honest limitations (v0.1)

- **No broadcasting.** Elementwise ops require exact shape match. This keeps
  the shape checker simple and total; broadcasting rules are a common
  source of off-by-one-dimension bugs and are deferred to a future version
  with a deliberately designed (not NumPy-inherited-by-accident) rule set.
- **Tensor elements are stored as `f64` at runtime regardless of declared
  dtype.** Dtype is a checked compile-time tag today, matching the class of
  bug (mixing float32 and float64 tensors) at the type level, but doesn't
  yet change in-memory representation. Narrower/packed storage is planned.
- **Indexing is rank-1 only.** Multi-dimensional indexing (`t[i][j]` or
  `t[i, j]`) is not yet implemented.
- **No registry.** `omlpkg` resolves path-based dependencies only; there's
  no remote index/`omlpkg add <name>` yet.
- **No recursive manifest resolution.** A dependency's *own* `import`
  statements resolve via sibling-file lookup, not its own `oml.toml` — so a
  dependency-of-a-dependency with its own manifest-declared deps isn't
  supported yet.
- **Interpreted, not compiled to native code.** `omlc`/`omlpkg run` and
  `overml_eval` all tree-walk the AST. A bytecode or native backend is future
  work; the type checker and module system are architected so a backend
  swap doesn't change the front end.

## Source map

| File | Responsibility |
|---|---|
| `src/lexer.rs` | characters -> tokens |
| `src/ast.rs` | AST + type grammar |
| `src/parser.rs` | tokens -> AST (recursive descent) |
| `src/typecheck.rs` | static shape/dtype checking, symbolic dim binding |
| `src/interp.rs` | tree-walking evaluator, tensor ops, provenance hashing |
| `src/rng.rs` | deterministic PRNG + FNV-1a hash |
| `src/modules.rs` | `import` resolution, function-name qualification |
| `src/pkg.rs` | `oml.toml`/`oml.lock` parsing and writing |
| `src/lib.rs` | C ABI (`overml_eval`/`overml_free_string`) |
| `src/bin/omlc.rs` | single-file compiler/runner CLI |
| `src/bin/omlpkg.rs` | package manager CLI |
| `bindings/python/overml/` | reference ctypes binding |
