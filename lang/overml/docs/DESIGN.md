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

Four specific, well-known ML-tooling pain points motivated the design:

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
4. **Unbounded KV cache growth ("KV bloat") during autoregressive
   inference.** A naive attention cache grows by one step every token
   decoded, with no ceiling — the classic long-context memory blowup.
   OverML's `KvCache` type is a fixed-capacity ring buffer: its *type*
   (`KvCache<dtype, [heads, capacity, head_dim]>`) fixes the backing
   allocation at construction, and pushing past capacity evicts the oldest
   step instead of growing. There is no sequence of `kv_push` calls that
   makes a `KvCache` bigger than its declared capacity — see "Bounded
   memory" below.

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
`rand_tensor(dtype, dims...)`, `provenance_hash()`, `kv_cache_new(dtype,
heads, capacity, head_dim)`, `kv_push(cache, step)`, `kv_cache_len(cache)`,
`kv_cache_get(cache, i)` — see "Bounded memory" below.

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

## Prehistoric lineage: flaws inherited from pre-C languages

"Prehistoric" here means literally that: the languages that existed before
C (1972) — FORTRAN (1957), Lisp (1958), ALGOL (1958/60), COBOL (1959), BASIC
(1964), PL/I (1964), B (1969, C's direct ancestor), and raw assembly. Each
has specific, well-documented design mistakes that later languages spent
decades fixing one at a time. This section lists the ones OverML fixes,
names the language(s) each mistake traces to, and points at the exact code
and test that proves the fix — no claim here is unverified prose.

One of these (lexical vs. dynamic scoping) was **found and fixed during the
writing of this section**, not designed in from the start — worth stating
plainly, because "we checked and it was actually broken" is a more honest
provenance than "we designed it correctly the first time."

| Flaw | Where it came from | How OverML avoids it | Proof |
|---|---|---|---|
| **Implicit/weak typing.** FORTRAN inferred a variable's type from its *first letter* (`I`–`N` meant integer, everything else real) — a typo in a variable name silently changed its type. PL/I coerced aggressively across types with surprising results. | FORTRAN, PL/I | Every tensor carries an explicit `dtype` and `shape` in its type; `i64`/`f64` mixing in an arithmetic op is a compile error, not a coercion. | `typecheck.rs`'s dtype/shape checks; `src/lib.rs::tests::shape_mismatch_is_rejected_at_check_time` |
| **Unstructured control flow.** FORTRAN, BASIC, and COBOL leaned on `GOTO`/line numbers for all control flow, producing famously unmaintainable "spaghetti code" (the subject of Dijkstra's 1968 "Go To Statement Considered Harmful"). | FORTRAN, BASIC, COBOL | OverML has no `goto` and no line-number-addressed jumps at all — only structured `if`/`else` and `while`, block-scoped by `{ }`. | `ast.rs`'s `Stmt` enum has no goto/label variant; the grammar in `parser.rs` has no way to construct one |
| **Dynamic scoping.** Early Lisp resolved a free variable using whatever binding happened to be active at the *call site*, not where the function was *defined* — so a callee could accidentally see (and be corrupted by) a caller's same-named local. Scheme and Common Lisp later fixed this. | Lisp (pre-Scheme) | A function call isolates the callee's execution to only `self.globals` plus its own fresh parameter scope — the caller's local variables are swapped out for the duration of the call, not inherited. | `interp.rs::call_user_fn`; `tests::scoping_is_lexical_not_dynamic_like_early_lisp` |
| **Call-by-name.** ALGOL's call-by-name parameters were textually re-evaluated on *every use* inside the callee, not once at the call. Combined with side effects, this produced results that depended on how many times a parameter happened to be referenced in the body (Jensen's Device is the canonical example/exploit of this). | ALGOL | Arguments are evaluated to concrete values once, before the callee's body runs at all (ordinary eager call-by-value). | `interp.rs::eval_call`'s user-function branch; `tests::call_by_value_is_eager_not_call_by_name` |
| **Silent integer overflow.** FORTRAN, B, and raw assembly all let arithmetic silently wrap or corrupt on overflow with no error; C inherited this as undefined behavior for signed integers. | FORTRAN, B, assembly | Integer `+`/`-`/`*`/`/` use Rust's checked arithmetic; overflow is a catchable runtime error, not a wrapped or undefined value. | `interp.rs::apply_int_op`; `tests::integer_overflow_is_a_checked_error_not_silent_wraparound` |
| **Unchecked array access.** FORTRAN, B, and assembly arrays have no bounds checking — an out-of-range index reads or corrupts adjacent memory instead of failing. | FORTRAN, B, assembly | Tensor indexing (`t[i]`) is bounds-checked against the actual backing storage on every access; out-of-range is a runtime error, never memory corruption (there's no raw memory access in OverML at all — no pointers, no `malloc`). | `interp.rs`'s `Expr::Index` handling; `tests::tensor_indexing_out_of_bounds_is_a_checked_error_not_memory_corruption` |
| **No package/dependency concept.** None of these languages had any notion of a versioned, namespaced dependency — programs were monolithic, or subroutines were linked by hand with no compatibility checking at all. | all of the above | `oml.toml`/`oml.lock` with content-hash-pinned dependencies and namespaced imports (`modname::fn`). | See "Packaging" below |
| **No reproducibility story.** Floating-point behavior varied by machine with no standard, and there was no concept of a seeded, portable random sequence — "run it again" could mean "get different numbers." | all of the above (this predates IEEE 754, 1985) | A from-scratch deterministic PRNG plus a provenance fingerprint of a run's full observable output. | See "Reproducibility" below |
| **Arbitrary, rigid surface syntax.** FORTRAN's fixed source columns (1–5 for labels, 6 for continuation, 7–72 for code) meant *where on the line* you typed something changed its meaning, independent of what you typed. | FORTRAN | Free-form syntax; whitespace is insignificant outside of separating tokens. | `lexer.rs`'s `skip_trivia` — no column tracking affects parsing |

What this section is *not* claiming: memory safety and lexical scoping
are not exotic OverML inventions — they're what most languages designed
after roughly 1975 do by default. The point of writing them down here is
that "prehistoric" flaws are specific, nameable, individually-fixable
mistakes, not a vague gesture at "old languages were bad" — and that
claim only means something if it's checked against the actual running
interpreter, which is exactly what the test column above does.

## Bounded memory: `KvCache` (reducing KV bloat)

```
// examples/kv_cache_window.oml
let cache = kv_cache_new("f32", 2, 3, 3);  // heads=2, capacity=3, head_dim=3

let i = 0;
while i < 5 {                              // 5 pushes...
    cache = kv_push(cache, rand_tensor("f32", 2, 3));
    i = i + 1;
}
print(kv_cache_len(cache));                 // ...but this prints 3, not 5
```

`KvCache<dtype, [heads, capacity, head_dim]>` (`src/interp.rs::KvCacheVal`) is
a fixed-capacity ring buffer over per-step `[heads, head_dim]` tensors. The
backing storage — `heads * capacity * head_dim` elements — is allocated once,
by `kv_cache_new`, and never resized. `kv_push` always writes into that same
array at a rotating cursor; once the cursor has wrapped, each write overwrites
the oldest surviving step (sliding-window / FIFO eviction, the same idea
behind "streaming" attention caches). `kv_cache_len` reports how many steps
are currently held (`<= capacity`, monotonically increasing until it hits the
ceiling, then constant forever), and `kv_cache_get(cache, i)` reads back the
`i`-th step in oldest-to-newest order, transparently accounting for the
wraparound.

The guarantee this buys you: **a `KvCache`'s memory footprint is fixed by its
type, not by how long the sequence runs.** There is no OverML program that
grows a `KvCache` past its declared capacity — `kv_push` is total (it always
returns a same-shaped `KvCache`, by construction, not by convention), so the
type checker doesn't even need a special rule to enforce the bound; the
ring-buffer semantics make it structurally impossible to violate. Contrast
with appending to a growing list/tensor every decode step, which has no such
ceiling and is exactly how KV caches balloon on long sequences in practice.

Deliberate v0.1 scope, consistent with the rest of the language:
- **Not generic.** All three `KvCache` dims (including `capacity`) must be
  concrete integer literals — capacity is a fixed compile-time budget, not a
  parameter a caller can leave symbolic. Using a symbol (e.g. `KvCache<f32,
  [H, 4, D]>`) is a parse error with a message explaining why.
- **Value semantics, like everything else in OverML.** `kv_push` returns an
  *updated* `KvCache`; it does not mutate its argument in place (OverML has
  no references). The idiom is the same as any other stateful loop in the
  language: `cache = kv_push(cache, step);`, mirroring `mut_i = mut_i + 1;`.
- **No dtype-driven memory savings yet.** Like `Tensor`, `KvCache` elements
  are stored as `f64` internally regardless of declared dtype (see "Honest
  limitations"). Pairing a narrower runtime representation with an `i8`/`i4`
  quantized `KvCache` dtype — a second, complementary way real systems cut KV
  memory — is natural future work once narrower tensor storage lands; it
  isn't implemented now rather than half-implemented.

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
| `src/interp.rs` | tree-walking evaluator, tensor ops, `KvCache` ring buffer, provenance hashing |
| `src/rng.rs` | deterministic PRNG + FNV-1a hash |
| `src/modules.rs` | `import` resolution, function-name qualification |
| `src/pkg.rs` | `oml.toml`/`oml.lock` parsing and writing |
| `src/lib.rs` | C ABI (`overml_eval`/`overml_free_string`) |
| `src/bin/omlc.rs` | single-file compiler/runner CLI |
| `src/bin/omlpkg.rs` | package manager CLI |
| `bindings/python/overml/` | reference ctypes binding |
