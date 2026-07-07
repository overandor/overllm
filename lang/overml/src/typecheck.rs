//! Static type checker. This is where OverML earns the "weak type safety
//! around tensors" fix: tensor types carry dtype + shape, matmul/elementwise
//! ops are checked for shape compatibility here (not at run time), and
//! generic functions bind symbolic dimensions (`Tensor<f32, [M, N]>`) from
//! their call-site arguments, verifying every use of `M` in a signature
//! agrees.
//!
//! Scope notes (v0.1): no shape broadcasting (exact-match only), no implicit
//! numeric coercion between i64/f64, tensor element storage is internally
//! f64 regardless of declared dtype (dtype is a checked compile-time tag —
//! narrower runtime storage is future work), indexing is only defined on
//! rank-1 tensors, and every tensor's shape must be fully concrete at
//! variable-binding time (symbolic dims only appear in function signatures).

use crate::ast::*;
use crate::error::{OResult, OverMlError};
use std::collections::HashMap;

#[derive(Clone, Debug)]
struct FnSig {
    params: Vec<Type>,
    ret: Type,
}

pub struct TypeChecker {
    fns: HashMap<String, FnSig>,
    scopes: Vec<HashMap<String, Type>>,
    /// True while checking the body of a function. Intermediate `let`s
    /// inside a generic function legitimately carry symbolic dims inherited
    /// from parameters (e.g. `let raw = a @ b;` where `a`/`b` are `Tensor<f32,
    /// [M, N]>`); only *top-level* state must be fully concrete, since there
    /// is no call site to bind its symbols against.
    in_fn: bool,
}

impl TypeChecker {
    pub fn new() -> Self {
        TypeChecker {
            fns: HashMap::new(),
            scopes: vec![HashMap::new()],
            in_fn: false,
        }
    }

    fn push_scope(&mut self) {
        self.scopes.push(HashMap::new());
    }

    fn pop_scope(&mut self) {
        self.scopes.pop();
    }

    fn declare(&mut self, name: &str, ty: Type) {
        self.scopes.last_mut().unwrap().insert(name.to_string(), ty);
    }

    fn lookup_var(&self, name: &str) -> Option<Type> {
        for scope in self.scopes.iter().rev() {
            if let Some(t) = scope.get(name) {
                return Some(t.clone());
            }
        }
        None
    }

    pub fn check_program(&mut self, prog: &Program) -> OResult<()> {
        for item in &prog.items {
            if let TopLevel::Fn(f) = item {
                if BUILTIN_NAMES.contains(&f.name.as_str()) {
                    return Err(OverMlError::detached(format!(
                        "function '{}' shadows a reserved builtin name",
                        f.name
                    )));
                }
                if self.fns.contains_key(&f.name) {
                    return Err(OverMlError::detached(format!(
                        "function '{}' is defined more than once",
                        f.name
                    )));
                }
                self.fns.insert(
                    f.name.clone(),
                    FnSig {
                        params: f.params.iter().map(|p| p.ty.clone()).collect(),
                        ret: f.ret.clone(),
                    },
                );
            }
        }

        for item in &prog.items {
            match item {
                TopLevel::Fn(f) => self.check_fn(f)?,
                TopLevel::Stmt(s) => {
                    self.check_stmt(s, &Type::Unit)?;
                }
            }
        }
        Ok(())
    }

    fn check_fn(&mut self, f: &FnDecl) -> OResult<()> {
        self.push_scope();
        for p in &f.params {
            self.declare(&p.name, p.ty.clone());
        }
        let prev_in_fn = self.in_fn;
        self.in_fn = true;
        let result = (|| {
            for s in &f.body {
                self.check_stmt(s, &f.ret)?;
            }
            Ok(())
        })();
        self.in_fn = prev_in_fn;
        self.pop_scope();
        result
    }

    fn check_stmt(&mut self, s: &Stmt, expected_ret: &Type) -> OResult<()> {
        match s {
            Stmt::Let(name, declared, expr) => {
                let inferred = self.type_of_with_hint(expr, declared.as_ref())?;
                let final_ty = match declared {
                    Some(dt) => {
                        if !types_equal(dt, &inferred) {
                            return Err(OverMlError::detached(format!(
                                "let '{}': declared type {} does not match expression type {}",
                                name, dt, inferred
                            )));
                        }
                        dt.clone()
                    }
                    None => inferred,
                };
                if !self.in_fn {
                    if let Type::Tensor(_, dims) = &final_ty {
                        for d in dims {
                            if let DimExpr::Sym(s) = d {
                                return Err(OverMlError::detached(format!(
                                    "let '{}': tensor dimension '{}' is symbolic; top-level variable bindings require fully concrete shapes",
                                    name, s
                                )));
                            }
                        }
                    }
                }
                self.declare(name, final_ty);
                Ok(())
            }
            Stmt::Assign(name, expr) => {
                let existing = self
                    .lookup_var(name)
                    .ok_or_else(|| OverMlError::detached(format!("assignment to undefined variable '{}'", name)))?;
                let t = self.type_of_with_hint(expr, Some(&existing))?;
                if !types_equal(&existing, &t) {
                    return Err(OverMlError::detached(format!(
                        "cannot assign {} to '{}' (declared as {})",
                        t, name, existing
                    )));
                }
                Ok(())
            }
            Stmt::ExprStmt(e) => {
                self.type_of(e)?;
                Ok(())
            }
            Stmt::Print(e) => {
                self.type_of(e)?;
                Ok(())
            }
            Stmt::If(cond, then_b, else_b) => {
                let ct = self.type_of(cond)?;
                if ct != Type::Bool {
                    return Err(OverMlError::detached(format!(
                        "if condition must be bool, found {}",
                        ct
                    )));
                }
                self.push_scope();
                for s in then_b {
                    self.check_stmt(s, expected_ret)?;
                }
                self.pop_scope();
                if let Some(eb) = else_b {
                    self.push_scope();
                    for s in eb {
                        self.check_stmt(s, expected_ret)?;
                    }
                    self.pop_scope();
                }
                Ok(())
            }
            Stmt::While(cond, body) => {
                let ct = self.type_of(cond)?;
                if ct != Type::Bool {
                    return Err(OverMlError::detached(format!(
                        "while condition must be bool, found {}",
                        ct
                    )));
                }
                self.push_scope();
                for s in body {
                    self.check_stmt(s, expected_ret)?;
                }
                self.pop_scope();
                Ok(())
            }
            Stmt::Return(None) => {
                if !types_equal(expected_ret, &Type::Unit) {
                    return Err(OverMlError::detached(format!(
                        "bare 'return' but function declares return type {}",
                        expected_ret
                    )));
                }
                Ok(())
            }
            Stmt::Return(Some(e)) => {
                let t = self.type_of(e)?;
                if !types_equal(expected_ret, &t) {
                    return Err(OverMlError::detached(format!(
                        "return type mismatch: function declares {}, got {}",
                        expected_ret, t
                    )));
                }
                Ok(())
            }
            Stmt::Import(_) => Ok(()), // resolved earlier by modules.rs
        }
    }

    fn type_of(&mut self, e: &Expr) -> OResult<Type> {
        self.type_of_with_hint(e, None)
    }

    fn type_of_with_hint(&mut self, e: &Expr, hint: Option<&Type>) -> OResult<Type> {
        match e {
            Expr::Int(_) => Ok(Type::I64),
            Expr::Float(_) => Ok(Type::F64),
            Expr::Bool(_) => Ok(Type::Bool),
            Expr::Str(_) => Ok(Type::Str),
            Expr::Ident(name) => self
                .lookup_var(name)
                .ok_or_else(|| OverMlError::detached(format!("undefined variable '{}'", name))),
            Expr::TensorLit(node) => {
                let shape = infer_lit_shape(node)?;
                let dtype = match hint {
                    Some(Type::Tensor(dt, dims)) => {
                        if dims.len() != shape.len()
                            || !dims.iter().zip(shape.iter()).all(|(d, n)| match d {
                                DimExpr::Lit(ln) => *ln == *n,
                                DimExpr::Sym(_) => false,
                            })
                        {
                            return Err(OverMlError::detached(format!(
                                "tensor literal shape {:?} does not match declared type {}",
                                shape, hint.unwrap()
                            )));
                        }
                        *dt
                    }
                    _ => Dtype::F32,
                };
                Ok(Type::Tensor(dtype, shape.into_iter().map(DimExpr::Lit).collect()))
            }
            Expr::Unary(op, inner) => {
                let t = self.type_of(inner)?;
                match op {
                    UnOp::Neg => match &t {
                        Type::I64 | Type::F64 => Ok(t),
                        Type::Tensor(_, _) => Ok(t),
                        other => Err(OverMlError::detached(format!("cannot negate {}", other))),
                    },
                    UnOp::Not => {
                        if t == Type::Bool {
                            Ok(Type::Bool)
                        } else {
                            Err(OverMlError::detached(format!("cannot apply '!' to {}", t)))
                        }
                    }
                }
            }
            Expr::Binary(op, l, r) => self.type_of_binary(*op, l, r),
            Expr::Call(name, args) => self.type_of_call(name, args),
            Expr::Index(base, idx) => {
                let bt = self.type_of(base)?;
                let it = self.type_of(idx)?;
                if it != Type::I64 {
                    return Err(OverMlError::detached(format!(
                        "tensor index must be i64, found {}",
                        it
                    )));
                }
                match bt {
                    Type::Tensor(_, dims) if dims.len() == 1 => Ok(Type::F64),
                    Type::Tensor(_, dims) => Err(OverMlError::detached(format!(
                        "indexing is only supported on rank-1 tensors in v0.1 (found rank {})",
                        dims.len()
                    ))),
                    other => Err(OverMlError::detached(format!("cannot index into {}", other))),
                }
            }
        }
    }

    fn type_of_binary(&mut self, op: BinOp, l: &Expr, r: &Expr) -> OResult<Type> {
        let lt = self.type_of(l)?;
        let rt = self.type_of(r)?;
        match op {
            BinOp::MatMul => match (&lt, &rt) {
                (Type::Tensor(dl, dims_l), Type::Tensor(dr, dims_r)) => {
                    if dims_l.len() != 2 || dims_r.len() != 2 {
                        return Err(OverMlError::detached(
                            "'@' (matmul) requires both operands to be rank-2 tensors".to_string(),
                        ));
                    }
                    if dl != dr {
                        return Err(OverMlError::detached(format!(
                            "matmul dtype mismatch: {} @ {}",
                            dl.name(),
                            dr.name()
                        )));
                    }
                    unify_dim(&dims_l[1], &dims_r[0]).map_err(OverMlError::detached)?;
                    Ok(Type::Tensor(*dl, vec![dims_l[0].clone(), dims_r[1].clone()]))
                }
                _ => Err(OverMlError::detached(format!(
                    "'@' (matmul) requires two rank-2 tensors, found {} @ {}",
                    lt, rt
                ))),
            },
            BinOp::Add | BinOp::Sub | BinOp::Mul | BinOp::Div => match (&lt, &rt) {
                (Type::Tensor(dl, sl), Type::Tensor(dr, sr)) => {
                    if dl != dr {
                        return Err(OverMlError::detached(format!(
                            "elementwise op dtype mismatch: {} vs {}",
                            dl.name(),
                            dr.name()
                        )));
                    }
                    if sl.len() != sr.len() || sl.iter().zip(sr.iter()).any(|(a, b)| unify_dim(a, b).is_err()) {
                        return Err(OverMlError::detached(format!(
                            "elementwise op shape mismatch: {} vs {} (OverML v0.1 does not broadcast)",
                            lt, rt
                        )));
                    }
                    Ok(Type::Tensor(*dl, sl.clone()))
                }
                (Type::I64, Type::I64) => Ok(Type::I64),
                (Type::F64, Type::F64) => Ok(Type::F64),
                (Type::I64, Type::F64) | (Type::F64, Type::I64) => Err(OverMlError::detached(format!(
                    "cannot mix i64 and f64 in '{:?}' without an explicit conversion",
                    op
                ))),
                _ => Err(OverMlError::detached(format!(
                    "operator '{:?}' not defined for {} and {}",
                    op, lt, rt
                ))),
            },
            BinOp::Eq | BinOp::Ne => {
                if !types_equal(&lt, &rt) {
                    return Err(OverMlError::detached(format!(
                        "cannot compare {} with {}",
                        lt, rt
                    )));
                }
                Ok(Type::Bool)
            }
            BinOp::Lt | BinOp::Gt | BinOp::Le | BinOp::Ge => match (&lt, &rt) {
                (Type::I64, Type::I64) | (Type::F64, Type::F64) => Ok(Type::Bool),
                _ => Err(OverMlError::detached(format!(
                    "comparison requires matching numeric operands, found {} and {}",
                    lt, rt
                ))),
            },
            BinOp::And | BinOp::Or => {
                if lt == Type::Bool && rt == Type::Bool {
                    Ok(Type::Bool)
                } else {
                    Err(OverMlError::detached(format!(
                        "'{:?}' requires bool operands, found {} and {}",
                        op, lt, rt
                    )))
                }
            }
        }
    }

    fn type_of_call(&mut self, name: &str, args: &[Expr]) -> OResult<Type> {
        match name {
            "seed" => {
                self.check_builtin_arity(name, args, 1)?;
                let t = self.type_of(&args[0])?;
                if t != Type::I64 {
                    return Err(OverMlError::detached("seed(n) expects an i64 argument".to_string()));
                }
                Ok(Type::Unit)
            }
            "zeros" | "ones" | "rand_tensor" => {
                if args.is_empty() {
                    return Err(OverMlError::detached(format!(
                        "{}(dtype, dims...) requires a dtype string argument",
                        name
                    )));
                }
                let dtype = match &args[0] {
                    Expr::Str(s) => Dtype::from_str(s)
                        .ok_or_else(|| OverMlError::detached(format!("unknown dtype '{}'", s)))?,
                    _ => {
                        return Err(OverMlError::detached(format!(
                            "{}: the dtype argument must be a string literal, e.g. \"f32\"",
                            name
                        )))
                    }
                };
                let mut dims = Vec::new();
                for a in &args[1..] {
                    match a {
                        Expr::Int(n) if *n >= 0 => dims.push(DimExpr::Lit(*n as usize)),
                        _ => {
                            return Err(OverMlError::detached(format!(
                                "{}: tensor dimensions must be non-negative integer literals",
                                name
                            )))
                        }
                    }
                }
                Ok(Type::Tensor(dtype, dims))
            }
            "provenance_hash" => {
                self.check_builtin_arity(name, args, 0)?;
                Ok(Type::Str)
            }
            _ => {
                let sig = self
                    .fns
                    .get(name)
                    .cloned()
                    .ok_or_else(|| OverMlError::detached(format!("call to undefined function '{}'", name)))?;
                if sig.params.len() != args.len() {
                    return Err(OverMlError::detached(format!(
                        "function '{}' expects {} argument(s), got {}",
                        name,
                        sig.params.len(),
                        args.len()
                    )));
                }
                let mut binding: HashMap<String, DimExpr> = HashMap::new();
                for (param_ty, arg_expr) in sig.params.iter().zip(args.iter()) {
                    let arg_ty = self.type_of(arg_expr)?;
                    bind_call_arg(param_ty, &arg_ty, &mut binding).map_err(|e| {
                        OverMlError::detached(format!("call to '{}': {}", name, e))
                    })?;
                }
                substitute_return(&sig.ret, &binding)
                    .map_err(|e| OverMlError::detached(format!("call to '{}': {}", name, e)))
            }
        }
    }

    fn check_builtin_arity(&self, name: &str, args: &[Expr], n: usize) -> OResult<()> {
        if args.len() != n {
            Err(OverMlError::detached(format!(
                "{}() expects {} argument(s), got {}",
                name,
                n,
                args.len()
            )))
        } else {
            Ok(())
        }
    }
}

impl Default for TypeChecker {
    fn default() -> Self {
        Self::new()
    }
}

fn types_equal(a: &Type, b: &Type) -> bool {
    match (a, b) {
        (Type::Tensor(da, sa), Type::Tensor(db, sb)) => {
            da == db && sa.len() == sb.len() && sa.iter().zip(sb.iter()).all(|(x, y)| dims_equal(x, y))
        }
        _ => a == b,
    }
}

fn dims_equal(a: &DimExpr, b: &DimExpr) -> bool {
    match (a, b) {
        (DimExpr::Lit(x), DimExpr::Lit(y)) => x == y,
        (DimExpr::Sym(x), DimExpr::Sym(y)) => x == y,
        _ => false,
    }
}

fn unify_dim(a: &DimExpr, b: &DimExpr) -> Result<(), String> {
    if dims_equal(a, b) {
        Ok(())
    } else {
        Err(format!("cannot unify dimension '{}' with '{}'", a, b))
    }
}

fn infer_lit_shape(node: &TensorLitNode) -> OResult<Vec<usize>> {
    match node {
        TensorLitNode::Scalar(_) => Ok(vec![]),
        TensorLitNode::List(items) => {
            if items.is_empty() {
                return Ok(vec![0]);
            }
            let first_shape = infer_lit_shape(&items[0])?;
            for it in &items[1..] {
                let s = infer_lit_shape(it)?;
                if s != first_shape {
                    return Err(OverMlError::detached(
                        "ragged tensor literal: all rows must have the same shape".to_string(),
                    ));
                }
            }
            let mut shape = vec![items.len()];
            shape.extend(first_shape);
            Ok(shape)
        }
    }
}

/// Binds/checks a function parameter's (possibly symbolic) type against a
/// concrete argument type, filling in `binding` the first time a symbol is
/// seen and checking agreement on subsequent uses.
fn bind_call_arg(param: &Type, arg: &Type, binding: &mut HashMap<String, DimExpr>) -> Result<(), String> {
    match (param, arg) {
        (Type::Tensor(pd, pdims), Type::Tensor(ad, adims)) => {
            if pd != ad {
                return Err(format!("dtype mismatch: expected {}, got {}", pd.name(), ad.name()));
            }
            if pdims.len() != adims.len() {
                return Err(format!(
                    "rank mismatch: expected rank {}, got rank {}",
                    pdims.len(),
                    adims.len()
                ));
            }
            for (pd, ad) in pdims.iter().zip(adims.iter()) {
                match pd {
                    DimExpr::Lit(n) => {
                        if !dims_equal(&DimExpr::Lit(*n), ad) {
                            return Err(format!("dimension mismatch: expected {}, got {}", pd, ad));
                        }
                    }
                    DimExpr::Sym(name) => match binding.get(name) {
                        Some(bound) => {
                            if !dims_equal(bound, ad) {
                                return Err(format!(
                                    "dimension '{}' was already bound to {}, but this argument has {}",
                                    name, bound, ad
                                ));
                            }
                        }
                        None => {
                            binding.insert(name.clone(), ad.clone());
                        }
                    },
                }
            }
            Ok(())
        }
        _ => {
            if types_equal(param, arg) {
                Ok(())
            } else {
                Err(format!("expected {}, got {}", param, arg))
            }
        }
    }
}

fn substitute_return(ret: &Type, binding: &HashMap<String, DimExpr>) -> Result<Type, String> {
    match ret {
        Type::Tensor(dt, dims) => {
            let mut out = Vec::with_capacity(dims.len());
            for d in dims {
                match d {
                    DimExpr::Lit(n) => out.push(DimExpr::Lit(*n)),
                    DimExpr::Sym(name) => match binding.get(name) {
                        Some(bound) => out.push(bound.clone()),
                        None => {
                            return Err(format!(
                                "return dimension '{}' is not determined by any parameter",
                                name
                            ))
                        }
                    },
                }
            }
            Ok(Type::Tensor(*dt, out))
        }
        other => Ok(other.clone()),
    }
}
