//! OverML: a small, statically shape-checked, deterministic-by-default
//! language for ML, compiled into a C-ABI shared library so it can be
//! imported as a package from any host language (Python, Node, Go, C++, ...)
//! the same way you'd import any native extension. See `docs/DESIGN.md` for
//! the language design and `bindings/python/` for a reference host binding.

pub mod ast;
pub mod error;
pub mod interp;
pub mod lexer;
pub mod modules;
pub mod parser;
pub mod pkg;
pub mod rng;
pub mod typecheck;

use error::OResult;
use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int};

/// Lex, parse, type-check, and run `src` with no filesystem access (so
/// `import` is not available through this entry point — use the `omlc`/
/// `omlpkg` CLIs, or shell out to them, when imports are needed).
///
/// Returns the captured stdout and the run's reproducibility fingerprint.
fn run_source(src: &str) -> OResult<(String, String)> {
    let tokens = lexer::Lexer::new(src).tokenize()?;
    let program = parser::Parser::new(tokens).parse_program()?;
    modules::reject_imports(&program)?;
    typecheck::TypeChecker::new().check_program(&program)?;
    let mut interp = interp::Interp::new(false);
    interp.eval_program(&program)?;
    let prov = interp.provenance_hex();
    Ok((interp.take_stdout(), prov))
}

/// C ABI entry point. On success (return 0): `*out_stdout` and
/// `*out_provenance` are set to newly-allocated, NUL-terminated strings that
/// the caller must free with `overml_free_string`; `*out_error` is left
/// null. On failure (return 1): `*out_error` is set instead, and the other
/// two out-params are left null.
///
/// # Safety
/// `source` must be a valid, NUL-terminated C string. `out_stdout`,
/// `out_provenance`, and `out_error` must each be a valid, non-null
/// `*mut *mut c_char`.
#[no_mangle]
pub unsafe extern "C" fn overml_eval(
    source: *const c_char,
    out_stdout: *mut *mut c_char,
    out_provenance: *mut *mut c_char,
    out_error: *mut *mut c_char,
) -> c_int {
    *out_stdout = std::ptr::null_mut();
    *out_provenance = std::ptr::null_mut();
    *out_error = std::ptr::null_mut();

    if source.is_null() {
        return set_error(out_error, "overml_eval: null source pointer");
    }
    let src = match CStr::from_ptr(source).to_str() {
        Ok(s) => s,
        Err(_) => return set_error(out_error, "overml_eval: source is not valid UTF-8"),
    };

    match run_source(src) {
        Ok((stdout, prov)) => {
            *out_stdout = to_c_string(stdout);
            *out_provenance = to_c_string(prov);
            0
        }
        Err(e) => set_error(out_error, &e.to_string()),
    }
}

/// Frees a string returned by `overml_eval`. Safe to call with null.
///
/// # Safety
/// `ptr` must be either null or a pointer previously returned by
/// `overml_eval` in one of its out-params, not already freed.
#[no_mangle]
pub unsafe extern "C" fn overml_free_string(ptr: *mut c_char) {
    if ptr.is_null() {
        return;
    }
    drop(CString::from_raw(ptr));
}

fn to_c_string(s: String) -> *mut c_char {
    // Embedded NULs can't survive a C string; replace rather than panic or
    // silently truncate, so callers never get corrupted/short output.
    let sanitized = if s.as_bytes().contains(&0) {
        s.replace('\0', "\u{FFFD}")
    } else {
        s
    };
    CString::new(sanitized)
        .unwrap_or_else(|_| CString::new("<overml: unrepresentable output>").unwrap())
        .into_raw()
}

unsafe fn set_error(out_error: *mut *mut c_char, msg: &str) -> c_int {
    *out_error = to_c_string(msg.to_string());
    1
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn run_source_executes_and_hashes_deterministically() {
        let src = r#"
            seed(42);
            let x: Tensor<f32, [2, 2]> = tensor([[1, 2], [3, 4]]);
            let y: Tensor<f32, [2, 2]> = tensor([[1, 0], [0, 1]]);
            print(x @ y);
        "#;
        let (out1, prov1) = run_source(src).unwrap();
        let (out2, prov2) = run_source(src).unwrap();
        assert_eq!(out1, out2);
        assert_eq!(prov1, prov2);
        assert!(out1.contains("[1, 2]"));
    }

    #[test]
    fn shape_mismatch_is_rejected_at_check_time() {
        let src = r#"
            let x: Tensor<f32, [2, 3]> = tensor([[1, 2, 3], [4, 5, 6]]);
            let y: Tensor<f32, [4, 2]> = tensor([[1, 2], [3, 4], [5, 6], [7, 8]]);
            print(x @ y);
        "#;
        assert!(run_source(src).is_err());
    }

    #[test]
    fn generic_function_binds_symbolic_dims() {
        let src = r#"
            fn dot(a: Tensor<f32, [N]>, b: Tensor<f32, [N]>) -> f64 {
                return 0.0;
            }
            let v: Tensor<f32, [3]> = tensor([1, 2, 3]);
            let w: Tensor<f32, [4]> = tensor([1, 2, 3, 4]);
            print(dot(v, w));
        "#;
        // N is bound to 3 by the first argument and to 4 by the second — a
        // genuine mismatch the checker must catch, not a runtime crash.
        let err = run_source(src).unwrap_err().to_string();
        assert!(
            err.contains("already bound to 3") && err.contains('4'),
            "expected a dimension-binding conflict, got: {}",
            err
        );
    }

    #[test]
    fn generic_function_with_consistent_dims_runs() {
        let src = r#"
            fn dot(a: Tensor<f32, [N]>, b: Tensor<f32, [N]>) -> f64 {
                return 0.0;
            }
            let v: Tensor<f32, [3]> = tensor([1, 2, 3]);
            let w: Tensor<f32, [3]> = tensor([4, 5, 6]);
            print(dot(v, w));
        "#;
        let (out, _) = run_source(src).unwrap();
        assert_eq!(out.trim(), "0");
    }

    #[test]
    fn kv_cache_length_is_bounded_by_capacity() {
        // Pushing 5 steps into a capacity-3 cache must never leave the
        // cache holding more than 3 — that bound is the whole point.
        let src = r#"
            let cache = kv_cache_new("f32", 2, 3, 4);
            let i = 0;
            while i < 5 {
                cache = kv_push(cache, zeros("f32", 2, 4));
                i = i + 1;
            }
            print(kv_cache_len(cache));
        "#;
        let (out, _) = run_source(src).unwrap();
        assert_eq!(out.trim(), "3");
    }

    #[test]
    fn kv_cache_evicts_oldest_first() {
        // heads=1, cap=2, head_dim=1. Push 0.0, 1.0, 2.0: 0.0 should be
        // evicted, leaving [1.0, 2.0] in chronological (oldest-first) order.
        let src = r#"
            let cache = kv_cache_new("f32", 1, 2, 1);
            cache = kv_push(cache, tensor([[0]]));
            cache = kv_push(cache, tensor([[1]]));
            cache = kv_push(cache, tensor([[2]]));
            print(kv_cache_get(cache, 0));
            print(kv_cache_get(cache, 1));
        "#;
        let (out, _) = run_source(src).unwrap();
        assert_eq!(out, "[[1]]\n[[2]]\n");
    }

    #[test]
    fn kv_cache_get_out_of_bounds_is_a_runtime_error() {
        let src = r#"
            let cache = kv_cache_new("f32", 1, 4, 1);
            cache = kv_push(cache, tensor([[1]]));
            print(kv_cache_get(cache, 1));
        "#;
        assert!(run_source(src).is_err());
    }

    #[test]
    fn kv_push_rejects_wrong_step_shape_at_check_time() {
        let src = r#"
            let cache = kv_cache_new("f32", 2, 4, 3);
            cache = kv_push(cache, zeros("f32", 2, 4));
        "#;
        assert!(run_source(src).is_err());
    }

    #[test]
    fn kv_cache_symbolic_dims_are_rejected_at_parse_time() {
        let src = r#"
            fn f(c: KvCache<f32, [H, 4, D]>) -> i64 { return 0; }
        "#;
        let err = run_source(src).unwrap_err().to_string();
        assert!(err.contains("compile-time bound"), "got: {}", err);
    }

    // --- "prehistoric lineage" regression tests: each of these locks in a
    // specific, well-documented flaw from a pre-C language that OverML is
    // designed not to repeat. See docs/DESIGN.md's "Prehistoric lineage"
    // section for the full list and historical citations.

    #[test]
    fn integer_overflow_is_a_checked_error_not_silent_wraparound() {
        // FORTRAN, B, and raw assembly all let arithmetic silently wrap or
        // corrupt on overflow; C inherited it as undefined behavior for
        // signed integers. OverML treats it as an ordinary runtime error.
        let src = "print(9223372036854775807 + 1);"; // i64::MAX + 1
        let err = run_source(src).unwrap_err().to_string();
        assert!(err.contains("overflow"), "expected an overflow error, got: {}", err);
    }

    #[test]
    fn integer_arithmetic_without_overflow_is_unaffected() {
        let (out, _) = run_source("print(40 + 2);").unwrap();
        assert_eq!(out.trim(), "42");
    }

    #[test]
    fn scoping_is_lexical_not_dynamic_like_early_lisp() {
        // Dynamic scoping (pre-Scheme/Common-Lisp Lisps) resolves a free
        // identifier using whatever local variable happens to be in scope
        // at the *call site*. Lexical scoping resolves it using the scope
        // where the function was *defined*. This is directly observable:
        // `show`'s only free variable is the global `x` — it must never
        // see `caller`'s local `x`, no matter that the call happens while
        // that local is in scope.
        let src = r#"
            let x = 100;
            fn show() -> i64 { return x; }
            fn caller() -> i64 {
                let x = 999;
                return show();
            }
            print(caller());
        "#;
        let (out, _) = run_source(src).unwrap();
        assert_eq!(
            out.trim(),
            "100",
            "show() must see the global x (lexical scoping), not caller()'s local x (dynamic scoping)"
        );
    }

    #[test]
    fn call_by_value_is_eager_not_call_by_name() {
        // ALGOL's call-by-name re-evaluated an argument expression on
        // every use inside the callee (Jensen's Device), which is exactly
        // the surprising behavior eager call-by-value avoids: an argument
        // expression is evaluated exactly once, before the callee runs.
        // Proof: `rand_tensor(...)` draws from a seeded, deterministic
        // sequence, so "the argument was evaluated once and reused" and
        // "the argument was re-evaluated per use" are two different,
        // predictable, distinguishable results.
        let double_body = r#"
            fn double(x: Tensor<f32, [1, 1]>) -> Tensor<f32, [1, 1]> {
                return x + x;
            }
            seed(42);
            print(double(rand_tensor("f32", 1, 1)));
        "#;
        let (double_out, _) = run_source(double_body).unwrap();

        // If the same first draw after seed(42) is used twice explicitly,
        // call-by-value semantics guarantee this matches double_out
        // exactly. Under (hypothetical) call-by-name, double() would have
        // consumed two draws instead of one, and this wouldn't match.
        let explicit_body = r#"
            seed(42);
            let v = rand_tensor("f32", 1, 1);
            print(v + v);
        "#;
        let (explicit_out, _) = run_source(explicit_body).unwrap();

        assert_eq!(
            double_out, explicit_out,
            "double(rand_tensor(...)) must equal v+v for a single draw v — \
             a mismatch means the argument was evaluated more than once"
        );
    }

    #[test]
    fn tensor_indexing_out_of_bounds_is_a_checked_error_not_memory_corruption() {
        // FORTRAN/B/raw assembly arrays have no bounds checking at all —
        // an out-of-range index reads or corrupts adjacent memory instead
        // of failing. OverML's tensors are backed by a Vec, and every
        // index is checked before use.
        let src = r#"
            let v: Tensor<f32, [3]> = tensor([1, 2, 3]);
            print(v[5]);
        "#;
        let err = run_source(src).unwrap_err().to_string();
        assert!(err.contains("out of bounds"), "expected a bounds error, got: {}", err);
    }

    #[test]
    fn ffi_roundtrip() {
        use std::ffi::CString;
        let src = CString::new("print(1 + 1);").unwrap();
        let mut out_stdout: *mut c_char = std::ptr::null_mut();
        let mut out_prov: *mut c_char = std::ptr::null_mut();
        let mut out_err: *mut c_char = std::ptr::null_mut();
        let rc = unsafe { overml_eval(src.as_ptr(), &mut out_stdout, &mut out_prov, &mut out_err) };
        assert_eq!(rc, 0);
        assert!(out_err.is_null());
        let stdout_s = unsafe { CStr::from_ptr(out_stdout) }.to_str().unwrap().to_string();
        assert_eq!(stdout_s.trim(), "2");
        unsafe {
            overml_free_string(out_stdout);
            overml_free_string(out_prov);
        }
    }
}
