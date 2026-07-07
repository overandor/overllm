//! `omlpkg` — the OverML package manager. v0.1 resolves path-based
//! dependencies declared in `oml.toml` and pins them by content hash in
//! `oml.lock`. A registry (`omlpkg add <name>` pulling from a remote index)
//! is intentionally out of scope for this first version — see
//! `docs/DESIGN.md` for the roadmap.

use overml::{interp, modules, pkg, typecheck};
use std::path::PathBuf;
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        print_usage();
        return ExitCode::FAILURE;
    }
    match args[1].as_str() {
        "init" => cmd_init(&args),
        "build" => cmd_build(&args, false),
        "run" => cmd_build(&args, true),
        other => {
            eprintln!("unknown command '{}'", other);
            print_usage();
            ExitCode::FAILURE
        }
    }
}

fn print_usage() {
    eprintln!("usage: omlpkg <init NAME | build | run> [--manifest DIR]");
}

fn cmd_init(args: &[String]) -> ExitCode {
    let Some(name) = args.get(2) else {
        eprintln!("usage: omlpkg init <name>");
        return ExitCode::FAILURE;
    };
    let dir = PathBuf::from(name);
    if dir.exists() {
        eprintln!("'{}' already exists", dir.display());
        return ExitCode::FAILURE;
    }
    if let Err(e) = std::fs::create_dir_all(&dir) {
        eprintln!("cannot create '{}': {}", dir.display(), e);
        return ExitCode::FAILURE;
    }
    let manifest = format!(
        "[package]\nname = \"{}\"\nversion = \"0.1.0\"\nentry = \"main.oml\"\n\n[dependencies]\n",
        name
    );
    let main_oml = "// entry point\nseed(0);\nprint(\"hello from OverML\");\n";
    if let Err(e) = std::fs::write(dir.join("oml.toml"), manifest) {
        eprintln!("cannot write oml.toml: {}", e);
        return ExitCode::FAILURE;
    }
    if let Err(e) = std::fs::write(dir.join("main.oml"), main_oml) {
        eprintln!("cannot write main.oml: {}", e);
        return ExitCode::FAILURE;
    }
    println!("created package '{}' in ./{}", name, name);
    ExitCode::SUCCESS
}

fn manifest_dir(args: &[String]) -> PathBuf {
    for i in 0..args.len() {
        if args[i] == "--manifest" {
            if let Some(p) = args.get(i + 1) {
                return PathBuf::from(p);
            }
        }
    }
    PathBuf::from(".")
}

fn cmd_build(args: &[String], run_after: bool) -> ExitCode {
    let dir = match manifest_dir(args).canonicalize() {
        Ok(d) => d,
        Err(e) => {
            eprintln!("cannot resolve manifest directory: {}", e);
            return ExitCode::FAILURE;
        }
    };
    let manifest_path = dir.join("oml.toml");
    let src = match std::fs::read_to_string(&manifest_path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("cannot read '{}': {}", manifest_path.display(), e);
            return ExitCode::FAILURE;
        }
    };
    let manifest = match pkg::parse_manifest(&src) {
        Ok(m) => m,
        Err(e) => {
            eprintln!("{}: {}", manifest_path.display(), e);
            return ExitCode::FAILURE;
        }
    };
    let resolved = pkg::resolve_dependency_paths(&manifest, &dir);
    let entry_path = dir.join(&manifest.entry);

    let program = match modules::load_program(&entry_path, Some(&resolved)) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("{}: {}", entry_path.display(), e);
            return ExitCode::FAILURE;
        }
    };
    if let Err(e) = typecheck::TypeChecker::new().check_program(&program) {
        eprintln!("{}: type error: {}", entry_path.display(), e);
        return ExitCode::FAILURE;
    }
    match pkg::write_lockfile(&manifest, &resolved, &dir) {
        Ok(lock_path) => println!("wrote {}", lock_path.display()),
        Err(e) => {
            eprintln!("{}", e);
            return ExitCode::FAILURE;
        }
    }
    println!("build OK: {} v{}", manifest.name, manifest.version);

    if run_after {
        let mut interp = interp::Interp::new(true);
        match interp.eval_program(&program) {
            Ok(()) => {
                println!("-- provenance: {} --", interp.provenance_hex());
                ExitCode::SUCCESS
            }
            Err(e) => {
                eprintln!("{}: runtime error: {}", entry_path.display(), e);
                ExitCode::FAILURE
            }
        }
    } else {
        ExitCode::SUCCESS
    }
}
