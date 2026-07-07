//! Import resolution. A `.oml` file can `import mod_name;` at the top
//! level; this module finds the corresponding source file, parses it,
//! recursively resolves *its* imports, and merges the imported functions
//! into the caller's namespace under a `mod_name::fn_name` prefix.
//!
//! Two resolution strategies, matching the two ways OverML programs run:
//!   1. Manifest-driven (`omlpkg`): `deps` maps a module name to the
//!      directory of a dependency declared in `oml.toml`, whose exposed
//!      surface is that directory's `lib.oml`.
//!   2. Sibling-file (`omlc` on a lone script, or a manifest dependency's
//!      own internal imports): look for `<name>.oml` next to the importing
//!      file. No manifest is consulted recursively inside a dependency in
//!      v0.1 — transitive manifest-driven deps are future work.
//!
//! Module files may only contain function declarations (no top-level
//! statements) — this keeps "what does importing X run" trivially answered
//! by "nothing, it just defines functions."

use crate::ast::*;
use crate::error::{OResult, OverMlError};
use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};

pub fn load_program(entry: &Path, deps: Option<&HashMap<String, PathBuf>>) -> OResult<Program> {
    let mut loading = HashSet::new();
    load_program_inner(entry, deps, &mut loading)
}

/// Used by the raw-source FFI entry point (`overml_eval`), which has no
/// filesystem context to resolve imports against.
pub fn reject_imports(program: &Program) -> OResult<()> {
    for item in &program.items {
        if let TopLevel::Stmt(Stmt::Import(name)) = item {
            return Err(OverMlError::detached(format!(
                "import '{}' is not supported via overml_eval (no filesystem context available); \
                 use the omlc/omlpkg CLIs to run files that have imports",
                name
            )));
        }
    }
    Ok(())
}

fn load_program_inner(
    entry: &Path,
    deps: Option<&HashMap<String, PathBuf>>,
    loading: &mut HashSet<PathBuf>,
) -> OResult<Program> {
    let canon = entry
        .canonicalize()
        .map_err(|e| OverMlError::detached(format!("cannot read '{}': {}", entry.display(), e)))?;
    if loading.contains(&canon) {
        return Err(OverMlError::detached(format!(
            "import cycle detected at '{}'",
            entry.display()
        )));
    }
    loading.insert(canon.clone());

    let src = std::fs::read_to_string(entry)?;
    let tokens = crate::lexer::Lexer::new(&src).tokenize()?;
    let mut program = crate::parser::Parser::new(tokens).parse_program()?;

    let dir = entry.parent().unwrap_or_else(|| Path::new("."));
    let mut kept = Vec::new();
    let mut modules_to_import: Vec<String> = Vec::new();
    for item in program.items.drain(..) {
        match item {
            TopLevel::Stmt(Stmt::Import(m)) => modules_to_import.push(m),
            other => kept.push(other),
        }
    }

    for module_name in modules_to_import {
        let module_path = resolve_module_path(&module_name, dir, deps)?;
        let sub = load_program_inner(&module_path, None, loading)?;
        let local_names: HashSet<String> = sub
            .items
            .iter()
            .filter_map(|it| match it {
                TopLevel::Fn(f) => Some(f.name.clone()),
                _ => None,
            })
            .collect();

        for it in sub.items {
            match it {
                TopLevel::Fn(mut f) => {
                    qualify_calls_stmts(&mut f.body, &module_name, &local_names);
                    f.name = format!("{}::{}", module_name, f.name);
                    kept.push(TopLevel::Fn(f));
                }
                TopLevel::Stmt(_) => {
                    return Err(OverMlError::detached(format!(
                        "module '{}' contains a top-level statement; imported modules may only contain function declarations",
                        module_name
                    )));
                }
            }
        }
    }

    program.items = kept;
    loading.remove(&canon);
    Ok(program)
}

fn resolve_module_path(
    name: &str,
    dir: &Path,
    deps: Option<&HashMap<String, PathBuf>>,
) -> OResult<PathBuf> {
    if let Some(deps) = deps {
        if let Some(p) = deps.get(name) {
            let f = p.join("lib.oml");
            if f.exists() {
                return Ok(f);
            }
            return Err(OverMlError::detached(format!(
                "dependency '{}' has no lib.oml at '{}'",
                name,
                p.display()
            )));
        }
    }
    let sibling = dir.join(format!("{}.oml", name));
    if sibling.exists() {
        return Ok(sibling);
    }
    Err(OverMlError::detached(format!(
        "cannot resolve import '{}': not declared under [dependencies] in oml.toml, and no sibling file '{}' exists",
        name,
        sibling.display()
    )))
}

fn qualify_calls_stmts(stmts: &mut [Stmt], module: &str, local: &HashSet<String>) {
    for s in stmts {
        qualify_calls_stmt(s, module, local);
    }
}

fn qualify_calls_stmt(s: &mut Stmt, module: &str, local: &HashSet<String>) {
    match s {
        Stmt::Let(_, _, e) => qualify_calls_expr(e, module, local),
        Stmt::Assign(_, e) => qualify_calls_expr(e, module, local),
        Stmt::ExprStmt(e) => qualify_calls_expr(e, module, local),
        Stmt::Print(e) => qualify_calls_expr(e, module, local),
        Stmt::If(c, then_b, else_b) => {
            qualify_calls_expr(c, module, local);
            qualify_calls_stmts(then_b, module, local);
            if let Some(eb) = else_b {
                qualify_calls_stmts(eb, module, local);
            }
        }
        Stmt::While(c, body) => {
            qualify_calls_expr(c, module, local);
            qualify_calls_stmts(body, module, local);
        }
        Stmt::Return(Some(e)) => qualify_calls_expr(e, module, local),
        Stmt::Return(None) | Stmt::Import(_) => {}
    }
}

fn qualify_calls_expr(e: &mut Expr, module: &str, local: &HashSet<String>) {
    match e {
        Expr::Call(name, args) => {
            if !name.contains("::") && local.contains(name) {
                *name = format!("{}::{}", module, name);
            }
            for a in args {
                qualify_calls_expr(a, module, local);
            }
        }
        Expr::Unary(_, inner) => qualify_calls_expr(inner, module, local),
        Expr::Binary(_, l, r) => {
            qualify_calls_expr(l, module, local);
            qualify_calls_expr(r, module, local);
        }
        Expr::Index(b, i) => {
            qualify_calls_expr(b, module, local);
            qualify_calls_expr(i, module, local);
        }
        Expr::Int(_) | Expr::Float(_) | Expr::Bool(_) | Expr::Str(_) | Expr::Ident(_) | Expr::TensorLit(_) => {}
    }
}
