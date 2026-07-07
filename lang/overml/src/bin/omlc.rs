//! `omlc` — the single-file OverML compiler/runner.
//!
//! `omlc check file.oml` type-checks only. `omlc run file.oml` type-checks
//! then interprets, echoing `print(...)` output live and finishing with the
//! run's reproducibility fingerprint.

use overml::{interp, modules, typecheck};
use std::path::PathBuf;
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 {
        eprintln!("usage: omlc <check|run> <file.oml>");
        return ExitCode::FAILURE;
    }
    let cmd = &args[1];
    let path = PathBuf::from(&args[2]);

    let program = match modules::load_program(&path, None) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("{}: {}", path.display(), e);
            return ExitCode::FAILURE;
        }
    };

    if let Err(e) = typecheck::TypeChecker::new().check_program(&program) {
        eprintln!("{}: type error: {}", path.display(), e);
        return ExitCode::FAILURE;
    }

    match cmd.as_str() {
        "check" => {
            println!("OK: {}", path.display());
            ExitCode::SUCCESS
        }
        "run" => {
            let mut interp = interp::Interp::new(true);
            match interp.eval_program(&program) {
                Ok(()) => {
                    println!("-- provenance: {} --", interp.provenance_hex());
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    eprintln!("{}: runtime error: {}", path.display(), e);
                    ExitCode::FAILURE
                }
            }
        }
        other => {
            eprintln!("unknown command '{}': expected 'check' or 'run'", other);
            ExitCode::FAILURE
        }
    }
}
