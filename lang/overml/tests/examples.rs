//! Runs every example under `examples/` end to end (lex -> parse -> import
//! resolution -> type check -> interpret), so a regression in any pipeline
//! stage fails `cargo test`, not just a manual `omlc run`.

use overml::{interp, modules, typecheck};
use std::path::Path;

fn run(path: &str) -> String {
    let p = Path::new(env!("CARGO_MANIFEST_DIR")).join(path);
    let program = modules::load_program(&p, None).expect("load");
    typecheck::TypeChecker::new()
        .check_program(&program)
        .expect("typecheck");
    let mut interp = interp::Interp::new(false);
    interp.eval_program(&program).expect("run");
    interp.take_stdout()
}

#[test]
fn hello_prints_expected_output() {
    let out = run("examples/hello.oml");
    assert_eq!(out, "hello from OverML\n7\n");
}

#[test]
fn tensor_shape_safety_computes_matmul() {
    let out = run("examples/tensor_shape_safety.oml");
    assert!(out.contains("[4, 5]"));
    assert!(out.contains("[10, 11]"));
}

#[test]
fn reproducible_training_is_deterministic_across_two_runs() {
    let a = run("examples/reproducible_training.oml");
    let b = run("examples/reproducible_training.oml");
    assert_eq!(a, b);
    // Same seed used twice within one run (`w` isn't re-seeded before the
    // loop) means every printed matrix in the trace is identical too.
    let lines: Vec<&str> = a.lines().collect();
    assert_eq!(lines[1], lines[2]);
}

#[test]
fn kv_cache_window_stays_bounded_and_is_deterministic() {
    let a = run("examples/kv_cache_window.oml");
    let b = run("examples/kv_cache_window.oml");
    assert_eq!(a, b, "same seed must reproduce identical cache contents");
    let lines: Vec<&str> = a.lines().collect();
    // First printed line is kv_cache_len after 5 pushes into a capacity-3
    // cache: must read 3, never 5 — that's the bloat-bound guarantee.
    assert_eq!(lines[0], "3");
    // len line + 3 retrieved steps + provenance line.
    assert_eq!(lines.len(), 5);
}

#[test]
fn manifest_driven_import_resolves_and_runs() {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("examples/pkg_demo");
    let manifest_src = std::fs::read_to_string(dir.join("oml.toml")).unwrap();
    let manifest = overml::pkg::parse_manifest(&manifest_src).unwrap();
    let resolved = overml::pkg::resolve_dependency_paths(&manifest, &dir);
    let entry = dir.join(&manifest.entry);
    let program = modules::load_program(&entry, Some(&resolved)).expect("load with deps");
    typecheck::TypeChecker::new()
        .check_program(&program)
        .expect("typecheck");
    let mut interp = interp::Interp::new(false);
    interp.eval_program(&program).expect("run");
    assert_eq!(interp.take_stdout(), "11\n");
}
