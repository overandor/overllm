use std::fmt;

/// A single compile- or run-time diagnostic, always carrying a source
/// location so tooling built on top of OverML can point at the exact
/// line/column instead of a generic "something went wrong".
#[derive(Debug, Clone)]
pub struct OverMlError {
    pub message: String,
    pub line: usize,
    pub col: usize,
}

impl OverMlError {
    pub fn new(message: impl Into<String>, line: usize, col: usize) -> Self {
        OverMlError {
            message: message.into(),
            line,
            col,
        }
    }

    /// For errors that don't originate from a specific source position
    /// (I/O errors, manifest errors, FFI boundary errors).
    pub fn detached(message: impl Into<String>) -> Self {
        OverMlError {
            message: message.into(),
            line: 0,
            col: 0,
        }
    }
}

impl fmt::Display for OverMlError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.line == 0 && self.col == 0 {
            write!(f, "{}", self.message)
        } else {
            write!(f, "{}:{}: {}", self.line, self.col, self.message)
        }
    }
}

impl std::error::Error for OverMlError {}

impl From<std::io::Error> for OverMlError {
    fn from(e: std::io::Error) -> Self {
        OverMlError::detached(format!("io error: {}", e))
    }
}

pub type OResult<T> = Result<T, OverMlError>;
