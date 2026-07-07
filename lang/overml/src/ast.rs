//! Abstract syntax tree for OverML, plus the type grammar. Tensor types
//! carry their shape as part of the type (`Tensor<f32, [2, 3]>`), and shape
//! dimensions can be integer literals or symbolic names (`Tensor<f32, [M, N]>`)
//! bound generically at a function's call sites. This is what lets the type
//! checker catch shape mismatches (e.g. matmul-ing a [2,3] against a [4,5])
//! before the program ever runs, instead of blowing up mid-training.

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Dtype {
    F32,
    F64,
    I32,
    I64,
    Bool,
}

impl Dtype {
    pub fn name(&self) -> &'static str {
        match self {
            Dtype::F32 => "f32",
            Dtype::F64 => "f64",
            Dtype::I32 => "i32",
            Dtype::I64 => "i64",
            Dtype::Bool => "bool",
        }
    }

    pub fn from_str(s: &str) -> Option<Dtype> {
        match s {
            "f32" => Some(Dtype::F32),
            "f64" => Some(Dtype::F64),
            "i32" => Some(Dtype::I32),
            "i64" => Some(Dtype::I64),
            "bool" => Some(Dtype::Bool),
            _ => None,
        }
    }
}

/// One dimension of a tensor shape: a fixed size, or a symbolic name that
/// gets bound when a generic function is called.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum DimExpr {
    Lit(usize),
    Sym(String),
}

impl std::fmt::Display for DimExpr {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DimExpr::Lit(n) => write!(f, "{}", n),
            DimExpr::Sym(s) => write!(f, "{}", s),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum Type {
    I64,
    F64,
    Bool,
    Str,
    Unit,
    Tensor(Dtype, Vec<DimExpr>),
}

impl std::fmt::Display for Type {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Type::I64 => write!(f, "i64"),
            Type::F64 => write!(f, "f64"),
            Type::Bool => write!(f, "bool"),
            Type::Str => write!(f, "str"),
            Type::Unit => write!(f, "()"),
            Type::Tensor(dt, dims) => {
                let dims_s: Vec<String> = dims.iter().map(|d| d.to_string()).collect();
                write!(f, "Tensor<{}, [{}]>", dt.name(), dims_s.join(", "))
            }
        }
    }
}

/// Nested literal used to write tensors inline, e.g. `tensor([[1, 2], [3, 4]])`.
/// Kept as a tree (not flattened) until type checking / eval, so shape can be
/// inferred and validated for raggedness.
#[derive(Debug, Clone)]
pub enum TensorLitNode {
    Scalar(f64),
    List(Vec<TensorLitNode>),
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum UnOp {
    Neg,
    Not,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum BinOp {
    Add,
    Sub,
    Mul,
    Div,
    MatMul,
    Eq,
    Ne,
    Lt,
    Gt,
    Le,
    Ge,
    And,
    Or,
}

#[derive(Debug, Clone)]
pub enum Expr {
    Int(i64),
    Float(f64),
    Bool(bool),
    Str(String),
    Ident(String),
    TensorLit(TensorLitNode),
    Unary(UnOp, Box<Expr>),
    Binary(BinOp, Box<Expr>, Box<Expr>),
    Call(String, Vec<Expr>),
    Index(Box<Expr>, Box<Expr>),
}

#[derive(Debug, Clone)]
pub enum Stmt {
    Let(String, Option<Type>, Expr),
    Assign(String, Expr),
    ExprStmt(Expr),
    Print(Expr),
    If(Expr, Vec<Stmt>, Option<Vec<Stmt>>),
    While(Expr, Vec<Stmt>),
    Return(Option<Expr>),
    Import(String),
}

#[derive(Debug, Clone)]
pub struct Param {
    pub name: String,
    pub ty: Type,
}

#[derive(Debug, Clone)]
pub struct FnDecl {
    pub name: String,
    pub params: Vec<Param>,
    pub ret: Type,
    pub body: Vec<Stmt>,
}

#[derive(Debug, Clone)]
pub enum TopLevel {
    Fn(FnDecl),
    Stmt(Stmt),
}

#[derive(Debug, Clone, Default)]
pub struct Program {
    pub items: Vec<TopLevel>,
}

/// Names reserved for builtins; user-defined functions may not shadow them.
pub const BUILTIN_NAMES: &[&str] = &["seed", "zeros", "ones", "rand_tensor", "provenance_hash"];
