//! Tree-walking interpreter. Runs *after* `typecheck::TypeChecker` has
//! accepted the program, so this file trusts shapes/dtypes/arity and only
//! guards against genuinely dynamic runtime failures (out-of-bounds index,
//! division by zero).

use crate::ast::*;
use crate::error::{OResult, OverMlError};
use crate::rng::{DeterministicRng, Fnv1a};
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct TensorVal {
    pub dtype: Dtype,
    pub shape: Vec<usize>,
    pub data: Vec<f64>,
}

/// A fixed-capacity ring buffer over `[heads, head_dim]` steps. `data` is
/// laid out as `[heads][cap][head_dim]` row-major and is allocated once, at
/// `heads * cap * head_dim`, and never resized — `kv_push` always writes
/// into that same backing array, wrapping `cursor` back to 0 once full. This
/// is the whole mechanism: the array's size is fixed at construction, so no
/// sequence of pushes can ever make it bigger.
#[derive(Debug, Clone)]
pub struct KvCacheVal {
    pub dtype: Dtype,
    pub heads: usize,
    pub cap: usize,
    pub head_dim: usize,
    pub data: Vec<f64>,
    pub cursor: usize,
    pub filled: usize,
}

#[derive(Debug, Clone)]
pub enum Value {
    I64(i64),
    F64(f64),
    Bool(bool),
    Str(String),
    Unit,
    Tensor(TensorVal),
    KvCache(KvCacheVal),
}

impl Value {
    fn as_i64(&self) -> i64 {
        match self {
            Value::I64(n) => *n,
            _ => unreachable!("type checker guarantees this is i64"),
        }
    }
    fn as_bool(&self) -> bool {
        match self {
            Value::Bool(b) => *b,
            _ => unreachable!("type checker guarantees this is bool"),
        }
    }
}

enum Flow {
    Normal,
    Return(Value),
}

pub struct Interp<'a> {
    fns: HashMap<String, &'a FnDecl>,
    scopes: Vec<HashMap<String, Value>>,
    rng: DeterministicRng,
    stdout: String,
    trace: Fnv1a,
    echo: bool,
}

impl<'a> Interp<'a> {
    pub fn new(echo: bool) -> Self {
        Interp {
            fns: HashMap::new(),
            scopes: vec![HashMap::new()],
            rng: DeterministicRng::new(0),
            stdout: String::new(),
            trace: Fnv1a::new(),
            echo,
        }
    }

    pub fn take_stdout(self) -> String {
        self.stdout
    }

    pub fn provenance_hex(&self) -> String {
        self.trace.finish_hex()
    }

    fn push_scope(&mut self) {
        self.scopes.push(HashMap::new());
    }
    fn pop_scope(&mut self) {
        self.scopes.pop();
    }
    fn declare(&mut self, name: &str, v: Value) {
        self.scopes.last_mut().unwrap().insert(name.to_string(), v);
    }
    fn lookup(&self, name: &str) -> Option<Value> {
        for scope in self.scopes.iter().rev() {
            if let Some(v) = scope.get(name) {
                return Some(v.clone());
            }
        }
        None
    }

    /// Updates a binding in whichever scope it lives in (found innermost
    /// first), rather than shadowing it in the current scope the way `let`
    /// does. Returns false if the type checker somehow let an assignment to
    /// an undefined variable through.
    fn set(&mut self, name: &str, v: Value) -> bool {
        for scope in self.scopes.iter_mut().rev() {
            if scope.contains_key(name) {
                scope.insert(name.to_string(), v);
                return true;
            }
        }
        false
    }

    pub fn eval_program(&mut self, prog: &'a Program) -> OResult<()> {
        for item in &prog.items {
            if let TopLevel::Fn(f) = item {
                self.fns.insert(f.name.clone(), f);
            }
        }
        for item in &prog.items {
            if let TopLevel::Stmt(s) = item {
                if let Flow::Return(_) = self.exec_stmt(s)? {
                    break;
                }
            }
        }
        Ok(())
    }

    fn exec_stmts(&mut self, stmts: &'a [Stmt]) -> OResult<Flow> {
        for s in stmts {
            match self.exec_stmt(s)? {
                Flow::Normal => {}
                ret @ Flow::Return(_) => return Ok(ret),
            }
        }
        Ok(Flow::Normal)
    }

    fn exec_stmt(&mut self, s: &'a Stmt) -> OResult<Flow> {
        match s {
            Stmt::Let(name, _ty, expr) => {
                let v = self.eval_expr(expr)?;
                self.declare(name, v);
                Ok(Flow::Normal)
            }
            Stmt::Assign(name, expr) => {
                let v = self.eval_expr(expr)?;
                if !self.set(name, v) {
                    unreachable!("type checker guarantees the variable was already declared");
                }
                Ok(Flow::Normal)
            }
            Stmt::ExprStmt(e) => {
                self.eval_expr(e)?;
                Ok(Flow::Normal)
            }
            Stmt::Print(e) => {
                let v = self.eval_expr(e)?;
                let text = format_value(&v);
                self.trace.write(text.as_bytes());
                if self.echo {
                    println!("{}", text);
                }
                self.stdout.push_str(&text);
                self.stdout.push('\n');
                Ok(Flow::Normal)
            }
            Stmt::If(cond, then_b, else_b) => {
                if self.eval_expr(cond)?.as_bool() {
                    self.push_scope();
                    let f = self.exec_stmts(then_b)?;
                    self.pop_scope();
                    Ok(f)
                } else if let Some(eb) = else_b {
                    self.push_scope();
                    let f = self.exec_stmts(eb)?;
                    self.pop_scope();
                    Ok(f)
                } else {
                    Ok(Flow::Normal)
                }
            }
            Stmt::While(cond, body) => {
                while self.eval_expr(cond)?.as_bool() {
                    self.push_scope();
                    let f = self.exec_stmts(body)?;
                    self.pop_scope();
                    if let Flow::Return(v) = f {
                        return Ok(Flow::Return(v));
                    }
                }
                Ok(Flow::Normal)
            }
            Stmt::Return(None) => Ok(Flow::Return(Value::Unit)),
            Stmt::Return(Some(e)) => {
                let v = self.eval_expr(e)?;
                Ok(Flow::Return(v))
            }
            Stmt::Import(_) => Ok(Flow::Normal),
        }
    }

    fn eval_expr(&mut self, e: &'a Expr) -> OResult<Value> {
        match e {
            Expr::Int(n) => Ok(Value::I64(*n)),
            Expr::Float(n) => Ok(Value::F64(*n)),
            Expr::Bool(b) => Ok(Value::Bool(*b)),
            Expr::Str(s) => Ok(Value::Str(s.clone())),
            Expr::Ident(name) => self
                .lookup(name)
                .ok_or_else(|| OverMlError::detached(format!("undefined variable '{}' at runtime", name))),
            Expr::TensorLit(node) => {
                let shape = lit_shape(node);
                let mut data = Vec::new();
                flatten_lit(node, &mut data);
                Ok(Value::Tensor(TensorVal {
                    dtype: Dtype::F32,
                    shape,
                    data,
                }))
            }
            Expr::Unary(op, inner) => {
                let v = self.eval_expr(inner)?;
                match (op, v) {
                    (UnOp::Neg, Value::I64(n)) => Ok(Value::I64(-n)),
                    (UnOp::Neg, Value::F64(n)) => Ok(Value::F64(-n)),
                    (UnOp::Neg, Value::Tensor(t)) => Ok(Value::Tensor(TensorVal {
                        data: t.data.iter().map(|x| -x).collect(),
                        ..t
                    })),
                    (UnOp::Not, Value::Bool(b)) => Ok(Value::Bool(!b)),
                    _ => unreachable!("type checker guarantees operand validity"),
                }
            }
            Expr::Binary(op, l, r) => self.eval_binary(*op, l, r),
            Expr::Call(name, args) => self.eval_call(name, args),
            Expr::Index(base, idx) => {
                let bv = self.eval_expr(base)?;
                let iv = self.eval_expr(idx)?.as_i64();
                match bv {
                    Value::Tensor(t) => {
                        if iv < 0 || iv as usize >= t.data.len() {
                            return Err(OverMlError::detached(format!(
                                "index {} out of bounds for tensor of length {}",
                                iv,
                                t.data.len()
                            )));
                        }
                        Ok(Value::F64(t.data[iv as usize]))
                    }
                    _ => unreachable!("type checker guarantees a tensor base"),
                }
            }
        }
    }

    fn eval_binary(&mut self, op: BinOp, l: &'a Expr, r: &'a Expr) -> OResult<Value> {
        // Short-circuit boolean operators.
        if op == BinOp::And {
            let lv = self.eval_expr(l)?.as_bool();
            if !lv {
                return Ok(Value::Bool(false));
            }
            return Ok(Value::Bool(self.eval_expr(r)?.as_bool()));
        }
        if op == BinOp::Or {
            let lv = self.eval_expr(l)?.as_bool();
            if lv {
                return Ok(Value::Bool(true));
            }
            return Ok(Value::Bool(self.eval_expr(r)?.as_bool()));
        }

        let lv = self.eval_expr(l)?;
        let rv = self.eval_expr(r)?;

        match op {
            BinOp::MatMul => {
                let (a, b) = match (lv, rv) {
                    (Value::Tensor(a), Value::Tensor(b)) => (a, b),
                    _ => unreachable!(),
                };
                let (m, n) = (a.shape[0], a.shape[1]);
                let p = b.shape[1];
                let mut data = vec![0.0f64; m * p];
                for i in 0..m {
                    for k in 0..n {
                        let a_ik = a.data[i * n + k];
                        if a_ik == 0.0 {
                            continue;
                        }
                        for j in 0..p {
                            data[i * p + j] += a_ik * b.data[k * p + j];
                        }
                    }
                }
                Ok(Value::Tensor(TensorVal {
                    dtype: a.dtype,
                    shape: vec![m, p],
                    data,
                }))
            }
            BinOp::Add | BinOp::Sub | BinOp::Mul | BinOp::Div => match (lv, rv) {
                (Value::Tensor(a), Value::Tensor(b)) => {
                    let data = a
                        .data
                        .iter()
                        .zip(b.data.iter())
                        .map(|(x, y)| apply_num_op(op, *x, *y))
                        .collect::<OResult<Vec<f64>>>()?;
                    Ok(Value::Tensor(TensorVal {
                        dtype: a.dtype,
                        shape: a.shape,
                        data,
                    }))
                }
                (Value::I64(a), Value::I64(b)) => Ok(Value::I64(apply_int_op(op, a, b)?)),
                (Value::F64(a), Value::F64(b)) => Ok(Value::F64(apply_num_op(op, a, b)?)),
                _ => unreachable!("type checker guarantees operand agreement"),
            },
            BinOp::Eq => Ok(Value::Bool(values_equal(&lv, &rv))),
            BinOp::Ne => Ok(Value::Bool(!values_equal(&lv, &rv))),
            BinOp::Lt | BinOp::Gt | BinOp::Le | BinOp::Ge => {
                let ord = match (lv, rv) {
                    (Value::I64(a), Value::I64(b)) => (a as f64).partial_cmp(&(b as f64)),
                    (Value::F64(a), Value::F64(b)) => a.partial_cmp(&b),
                    _ => unreachable!(),
                }
                .ok_or_else(|| OverMlError::detached("comparison with NaN".to_string()))?;
                let b = match op {
                    BinOp::Lt => ord.is_lt(),
                    BinOp::Gt => ord.is_gt(),
                    BinOp::Le => ord.is_le(),
                    BinOp::Ge => ord.is_ge(),
                    _ => unreachable!(),
                };
                Ok(Value::Bool(b))
            }
            BinOp::And | BinOp::Or => unreachable!("handled above via short-circuit"),
        }
    }

    fn eval_call(&mut self, name: &str, args: &'a [Expr]) -> OResult<Value> {
        match name {
            "seed" => {
                let n = self.eval_expr(&args[0])?.as_i64();
                self.rng = DeterministicRng::new(n as u64);
                self.trace.write(b"seed:");
                self.trace.write_u64(n as u64);
                Ok(Value::Unit)
            }
            "zeros" | "ones" | "rand_tensor" => {
                let dtype = match self.eval_expr(&args[0])? {
                    Value::Str(s) => Dtype::from_str(&s).unwrap(),
                    _ => unreachable!(),
                };
                let mut shape = Vec::new();
                for a in &args[1..] {
                    shape.push(self.eval_expr(a)?.as_i64() as usize);
                }
                // `product()` on an empty shape (a rank-0/scalar tensor) is 1,
                // the multiplicative identity — exactly the single element we want.
                let count: usize = shape.iter().product();
                let data = match name {
                    "zeros" => vec![0.0; count],
                    "ones" => vec![1.0; count],
                    "rand_tensor" => {
                        let mut d = Vec::with_capacity(count);
                        for _ in 0..count {
                            let v = self.rng.next_f64();
                            self.trace.write_f64(v);
                            d.push(v);
                        }
                        d
                    }
                    _ => unreachable!(),
                };
                Ok(Value::Tensor(TensorVal { dtype, shape, data }))
            }
            "provenance_hash" => Ok(Value::Str(self.trace.finish_hex())),
            "kv_cache_new" => {
                let dtype = match self.eval_expr(&args[0])? {
                    Value::Str(s) => Dtype::from_str(&s).unwrap(),
                    _ => unreachable!(),
                };
                let heads = self.eval_expr(&args[1])?.as_i64() as usize;
                let cap = self.eval_expr(&args[2])?.as_i64() as usize;
                let head_dim = self.eval_expr(&args[3])?.as_i64() as usize;
                Ok(Value::KvCache(KvCacheVal {
                    dtype,
                    heads,
                    cap,
                    head_dim,
                    data: vec![0.0; heads * cap * head_dim],
                    cursor: 0,
                    filled: 0,
                }))
            }
            "kv_push" => {
                let cache = match self.eval_expr(&args[0])? {
                    Value::KvCache(c) => c,
                    _ => unreachable!(),
                };
                let step = match self.eval_expr(&args[1])? {
                    Value::Tensor(t) => t,
                    _ => unreachable!(),
                };
                let KvCacheVal {
                    dtype,
                    heads,
                    cap,
                    head_dim,
                    mut data,
                    cursor,
                    filled,
                } = cache;
                // Overwrite the slot at `cursor` across every head — this is
                // the sliding-window eviction: once full, the oldest step is
                // exactly the one `cursor` is about to clobber.
                for h in 0..heads {
                    for d in 0..head_dim {
                        data[h * cap * head_dim + cursor * head_dim + d] = step.data[h * head_dim + d];
                    }
                }
                Ok(Value::KvCache(KvCacheVal {
                    dtype,
                    heads,
                    cap,
                    head_dim,
                    data,
                    cursor: (cursor + 1) % cap,
                    filled: (filled + 1).min(cap),
                }))
            }
            "kv_cache_len" => match self.eval_expr(&args[0])? {
                Value::KvCache(c) => Ok(Value::I64(c.filled as i64)),
                _ => unreachable!(),
            },
            "kv_cache_get" => {
                let cache = match self.eval_expr(&args[0])? {
                    Value::KvCache(c) => c,
                    _ => unreachable!(),
                };
                let i = self.eval_expr(&args[1])?.as_i64();
                if i < 0 || i as usize >= cache.filled {
                    return Err(OverMlError::detached(format!(
                        "kv_cache_get: index {} out of bounds for {} filled entries",
                        i, cache.filled
                    )));
                }
                let i = i as usize;
                // Chronological index -> ring position. Before the buffer
                // wraps, oldest-first order *is* array order. Once full, the
                // oldest entry sits at `cursor` (next slot to be overwritten).
                let pos = if cache.filled < cache.cap {
                    i
                } else {
                    (cache.cursor + i) % cache.cap
                };
                let mut out = Vec::with_capacity(cache.heads * cache.head_dim);
                for h in 0..cache.heads {
                    for d in 0..cache.head_dim {
                        out.push(cache.data[h * cache.cap * cache.head_dim + pos * cache.head_dim + d]);
                    }
                }
                Ok(Value::Tensor(TensorVal {
                    dtype: cache.dtype,
                    shape: vec![cache.heads, cache.head_dim],
                    data: out,
                }))
            }
            _ => {
                let f: &FnDecl = self
                    .fns
                    .get(name)
                    .copied()
                    .ok_or_else(|| OverMlError::detached(format!("call to undefined function '{}'", name)))?;
                let mut arg_vals = Vec::with_capacity(args.len());
                for a in args {
                    arg_vals.push(self.eval_expr(a)?);
                }
                self.push_scope();
                for (p, v) in f.params.iter().zip(arg_vals.into_iter()) {
                    self.declare(&p.name, v);
                }
                let result = match self.exec_stmts(&f.body)? {
                    Flow::Return(v) => v,
                    Flow::Normal => Value::Unit,
                };
                self.pop_scope();
                Ok(result)
            }
        }
    }
}

fn apply_int_op(op: BinOp, a: i64, b: i64) -> OResult<i64> {
    match op {
        BinOp::Add => Ok(a.wrapping_add(b)),
        BinOp::Sub => Ok(a.wrapping_sub(b)),
        BinOp::Mul => Ok(a.wrapping_mul(b)),
        BinOp::Div => {
            if b == 0 {
                Err(OverMlError::detached("integer division by zero".to_string()))
            } else {
                Ok(a / b)
            }
        }
        _ => unreachable!(),
    }
}

fn apply_num_op(op: BinOp, a: f64, b: f64) -> OResult<f64> {
    match op {
        BinOp::Add => Ok(a + b),
        BinOp::Sub => Ok(a - b),
        BinOp::Mul => Ok(a * b),
        BinOp::Div => Ok(a / b),
        _ => unreachable!(),
    }
}

fn values_equal(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::I64(x), Value::I64(y)) => x == y,
        (Value::F64(x), Value::F64(y)) => x == y,
        (Value::Bool(x), Value::Bool(y)) => x == y,
        (Value::Str(x), Value::Str(y)) => x == y,
        (Value::Unit, Value::Unit) => true,
        (Value::Tensor(x), Value::Tensor(y)) => x.shape == y.shape && x.data == y.data,
        (Value::KvCache(x), Value::KvCache(y)) => {
            x.dtype == y.dtype
                && x.heads == y.heads
                && x.cap == y.cap
                && x.head_dim == y.head_dim
                && x.cursor == y.cursor
                && x.filled == y.filled
                && x.data == y.data
        }
        _ => false,
    }
}

fn lit_shape(node: &TensorLitNode) -> Vec<usize> {
    match node {
        TensorLitNode::Scalar(_) => vec![],
        TensorLitNode::List(items) => {
            if items.is_empty() {
                return vec![0];
            }
            let mut shape = vec![items.len()];
            shape.extend(lit_shape(&items[0]));
            shape
        }
    }
}

fn flatten_lit(node: &TensorLitNode, out: &mut Vec<f64>) {
    match node {
        TensorLitNode::Scalar(v) => out.push(*v),
        TensorLitNode::List(items) => {
            for it in items {
                flatten_lit(it, out);
            }
        }
    }
}

fn format_value(v: &Value) -> String {
    match v {
        Value::I64(n) => n.to_string(),
        Value::F64(n) => n.to_string(),
        Value::Bool(b) => b.to_string(),
        Value::Str(s) => s.clone(),
        Value::Unit => "()".to_string(),
        Value::Tensor(t) => format_tensor(t),
        Value::KvCache(c) => format!(
            "KvCache<{}, heads={}, cap={}, head_dim={}, filled={}>",
            c.dtype.name(),
            c.heads,
            c.cap,
            c.head_dim,
            c.filled
        ),
    }
}

fn format_tensor(t: &TensorVal) -> String {
    fn rec(shape: &[usize], data: &[f64]) -> String {
        if shape.is_empty() {
            return format!("{}", data[0]);
        }
        let (head, rest) = (shape[0], &shape[1..]);
        let chunk_len: usize = rest.iter().product::<usize>().max(1);
        let mut parts = Vec::with_capacity(head);
        for i in 0..head {
            let start = i * chunk_len;
            let end = start + chunk_len;
            parts.push(rec(rest, &data[start..end]));
        }
        format!("[{}]", parts.join(", "))
    }
    rec(&t.shape, &t.data)
}
