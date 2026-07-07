//! Recursive-descent parser: `Vec<Spanned<Token>>` -> `ast::Program`.

use crate::ast::*;
use crate::error::{OResult, OverMlError};
use crate::lexer::{Spanned, Token};

pub struct Parser {
    toks: Vec<Spanned>,
    pos: usize,
}

impl Parser {
    pub fn new(toks: Vec<Spanned>) -> Self {
        Parser { toks, pos: 0 }
    }

    fn cur(&self) -> &Token {
        &self.toks[self.pos].tok
    }

    fn cur_pos(&self) -> (usize, usize) {
        (self.toks[self.pos].line, self.toks[self.pos].col)
    }

    fn bump(&mut self) -> Token {
        let t = self.toks[self.pos].tok.clone();
        if self.pos + 1 < self.toks.len() {
            self.pos += 1;
        }
        t
    }

    fn err(&self, msg: impl Into<String>) -> OverMlError {
        let (line, col) = self.cur_pos();
        OverMlError::new(msg, line, col)
    }

    fn expect(&mut self, tok: Token) -> OResult<()> {
        if *self.cur() == tok {
            self.bump();
            Ok(())
        } else {
            Err(self.err(format!("expected {:?}, found {:?}", tok, self.cur())))
        }
    }

    fn expect_ident(&mut self) -> OResult<String> {
        match self.cur().clone() {
            Token::Ident(s) => {
                self.bump();
                Ok(s)
            }
            other => Err(self.err(format!("expected identifier, found {:?}", other))),
        }
    }

    pub fn parse_program(&mut self) -> OResult<Program> {
        let mut items = Vec::new();
        while *self.cur() != Token::Eof {
            items.push(self.parse_top_level()?);
        }
        Ok(Program { items })
    }

    fn parse_top_level(&mut self) -> OResult<TopLevel> {
        match self.cur() {
            Token::KwFn => Ok(TopLevel::Fn(self.parse_fn_decl()?)),
            _ => Ok(TopLevel::Stmt(self.parse_stmt()?)),
        }
    }

    fn parse_fn_decl(&mut self) -> OResult<FnDecl> {
        self.expect(Token::KwFn)?;
        let name = self.expect_ident()?;
        self.expect(Token::LParen)?;
        let mut params = Vec::new();
        while *self.cur() != Token::RParen {
            let pname = self.expect_ident()?;
            self.expect(Token::Colon)?;
            let ty = self.parse_type()?;
            params.push(Param { name: pname, ty });
            if *self.cur() == Token::Comma {
                self.bump();
            } else {
                break;
            }
        }
        self.expect(Token::RParen)?;
        let ret = if *self.cur() == Token::Arrow {
            self.bump();
            self.parse_type()?
        } else {
            Type::Unit
        };
        let body = self.parse_block()?;
        Ok(FnDecl {
            name,
            params,
            ret,
            body,
        })
    }

    fn parse_type(&mut self) -> OResult<Type> {
        let name = self.expect_ident()?;
        match name.as_str() {
            "i64" => Ok(Type::I64),
            "f64" => Ok(Type::F64),
            "bool" => Ok(Type::Bool),
            "str" => Ok(Type::Str),
            "Tensor" => {
                self.expect(Token::Lt)?;
                let dtype_name = self.expect_ident()?;
                let dtype = Dtype::from_str(&dtype_name)
                    .ok_or_else(|| self.err(format!("unknown tensor dtype '{}'", dtype_name)))?;
                self.expect(Token::Comma)?;
                self.expect(Token::LBracket)?;
                let mut dims = Vec::new();
                while *self.cur() != Token::RBracket {
                    let dim = match self.cur().clone() {
                        Token::Int(n) => {
                            if n < 0 {
                                return Err(self.err("tensor dimensions must be non-negative"));
                            }
                            self.bump();
                            DimExpr::Lit(n as usize)
                        }
                        Token::Ident(s) => {
                            self.bump();
                            DimExpr::Sym(s)
                        }
                        other => {
                            return Err(self.err(format!(
                                "expected a dimension (integer or symbol), found {:?}",
                                other
                            )))
                        }
                    };
                    dims.push(dim);
                    if *self.cur() == Token::Comma {
                        self.bump();
                    } else {
                        break;
                    }
                }
                self.expect(Token::RBracket)?;
                self.expect(Token::Gt)?;
                Ok(Type::Tensor(dtype, dims))
            }
            "KvCache" => {
                self.expect(Token::Lt)?;
                let dtype_name = self.expect_ident()?;
                let dtype = Dtype::from_str(&dtype_name)
                    .ok_or_else(|| self.err(format!("unknown tensor dtype '{}'", dtype_name)))?;
                self.expect(Token::Comma)?;
                self.expect(Token::LBracket)?;
                let mut dims = Vec::new();
                while *self.cur() != Token::RBracket {
                    match self.cur().clone() {
                        Token::Int(n) => {
                            if n <= 0 {
                                return Err(self.err("KvCache dimensions must be positive integers"));
                            }
                            self.bump();
                            dims.push(DimExpr::Lit(n as usize));
                        }
                        Token::Ident(s) => {
                            return Err(self.err(format!(
                                "KvCache dimensions must be concrete integers (found symbolic '{}'): capacity is a fixed compile-time bound, not a generic parameter",
                                s
                            )));
                        }
                        other => {
                            return Err(self.err(format!("expected a positive integer dimension, found {:?}", other)))
                        }
                    };
                    if *self.cur() == Token::Comma {
                        self.bump();
                    } else {
                        break;
                    }
                }
                self.expect(Token::RBracket)?;
                self.expect(Token::Gt)?;
                if dims.len() != 3 {
                    return Err(self.err(format!(
                        "KvCache requires exactly 3 dimensions [heads, capacity, head_dim], found {}",
                        dims.len()
                    )));
                }
                Ok(Type::KvCache(dtype, dims))
            }
            other => Err(self.err(format!("unknown type '{}'", other))),
        }
    }

    fn parse_block(&mut self) -> OResult<Vec<Stmt>> {
        self.expect(Token::LBrace)?;
        let mut stmts = Vec::new();
        while *self.cur() != Token::RBrace {
            stmts.push(self.parse_stmt()?);
        }
        self.expect(Token::RBrace)?;
        Ok(stmts)
    }

    fn parse_stmt(&mut self) -> OResult<Stmt> {
        match self.cur().clone() {
            Token::KwLet => {
                self.bump();
                let name = self.expect_ident()?;
                let ty = if *self.cur() == Token::Colon {
                    self.bump();
                    Some(self.parse_type()?)
                } else {
                    None
                };
                self.expect(Token::Eq)?;
                let expr = self.parse_expr()?;
                self.expect(Token::Semi)?;
                Ok(Stmt::Let(name, ty, expr))
            }
            Token::KwPrint => {
                self.bump();
                self.expect(Token::LParen)?;
                let e = self.parse_expr()?;
                self.expect(Token::RParen)?;
                self.expect(Token::Semi)?;
                Ok(Stmt::Print(e))
            }
            Token::KwIf => {
                self.bump();
                let cond = self.parse_expr()?;
                let then_b = self.parse_block()?;
                let else_b = if *self.cur() == Token::KwElse {
                    self.bump();
                    if *self.cur() == Token::KwIf {
                        let inner = self.parse_stmt()?;
                        Some(vec![inner])
                    } else {
                        Some(self.parse_block()?)
                    }
                } else {
                    None
                };
                Ok(Stmt::If(cond, then_b, else_b))
            }
            Token::KwWhile => {
                self.bump();
                let cond = self.parse_expr()?;
                let body = self.parse_block()?;
                Ok(Stmt::While(cond, body))
            }
            Token::KwReturn => {
                self.bump();
                if *self.cur() == Token::Semi {
                    self.bump();
                    Ok(Stmt::Return(None))
                } else {
                    let e = self.parse_expr()?;
                    self.expect(Token::Semi)?;
                    Ok(Stmt::Return(Some(e)))
                }
            }
            Token::KwImport => {
                self.bump();
                let name = self.expect_ident()?;
                self.expect(Token::Semi)?;
                Ok(Stmt::Import(name))
            }
            Token::Ident(name) if *self.peek_ahead(1) == Token::Eq => {
                self.bump(); // identifier
                self.bump(); // '='
                let e = self.parse_expr()?;
                self.expect(Token::Semi)?;
                Ok(Stmt::Assign(name, e))
            }
            _ => {
                let e = self.parse_expr()?;
                self.expect(Token::Semi)?;
                Ok(Stmt::ExprStmt(e))
            }
        }
    }

    fn peek_ahead(&self, n: usize) -> &Token {
        let idx = (self.pos + n).min(self.toks.len() - 1);
        &self.toks[idx].tok
    }

    // --- expressions, precedence climbing, lowest to highest ---

    fn parse_expr(&mut self) -> OResult<Expr> {
        self.parse_or()
    }

    fn parse_or(&mut self) -> OResult<Expr> {
        let mut lhs = self.parse_and()?;
        while *self.cur() == Token::OrOr {
            self.bump();
            let rhs = self.parse_and()?;
            lhs = Expr::Binary(BinOp::Or, Box::new(lhs), Box::new(rhs));
        }
        Ok(lhs)
    }

    fn parse_and(&mut self) -> OResult<Expr> {
        let mut lhs = self.parse_equality()?;
        while *self.cur() == Token::AndAnd {
            self.bump();
            let rhs = self.parse_equality()?;
            lhs = Expr::Binary(BinOp::And, Box::new(lhs), Box::new(rhs));
        }
        Ok(lhs)
    }

    fn parse_equality(&mut self) -> OResult<Expr> {
        let mut lhs = self.parse_comparison()?;
        loop {
            let op = match self.cur() {
                Token::EqEq => BinOp::Eq,
                Token::NotEq => BinOp::Ne,
                _ => break,
            };
            self.bump();
            let rhs = self.parse_comparison()?;
            lhs = Expr::Binary(op, Box::new(lhs), Box::new(rhs));
        }
        Ok(lhs)
    }

    fn parse_comparison(&mut self) -> OResult<Expr> {
        let mut lhs = self.parse_additive()?;
        loop {
            let op = match self.cur() {
                Token::Lt => BinOp::Lt,
                Token::Gt => BinOp::Gt,
                Token::Le => BinOp::Le,
                Token::Ge => BinOp::Ge,
                _ => break,
            };
            self.bump();
            let rhs = self.parse_additive()?;
            lhs = Expr::Binary(op, Box::new(lhs), Box::new(rhs));
        }
        Ok(lhs)
    }

    fn parse_additive(&mut self) -> OResult<Expr> {
        let mut lhs = self.parse_multiplicative()?;
        loop {
            let op = match self.cur() {
                Token::Plus => BinOp::Add,
                Token::Minus => BinOp::Sub,
                _ => break,
            };
            self.bump();
            let rhs = self.parse_multiplicative()?;
            lhs = Expr::Binary(op, Box::new(lhs), Box::new(rhs));
        }
        Ok(lhs)
    }

    fn parse_multiplicative(&mut self) -> OResult<Expr> {
        let mut lhs = self.parse_unary()?;
        loop {
            let op = match self.cur() {
                Token::Star => BinOp::Mul,
                Token::Slash => BinOp::Div,
                Token::At => BinOp::MatMul,
                _ => break,
            };
            self.bump();
            let rhs = self.parse_unary()?;
            lhs = Expr::Binary(op, Box::new(lhs), Box::new(rhs));
        }
        Ok(lhs)
    }

    fn parse_unary(&mut self) -> OResult<Expr> {
        match self.cur() {
            Token::Minus => {
                self.bump();
                Ok(Expr::Unary(UnOp::Neg, Box::new(self.parse_unary()?)))
            }
            Token::Bang => {
                self.bump();
                Ok(Expr::Unary(UnOp::Not, Box::new(self.parse_unary()?)))
            }
            _ => self.parse_postfix(),
        }
    }

    fn parse_postfix(&mut self) -> OResult<Expr> {
        let mut e = self.parse_primary()?;
        loop {
            if *self.cur() == Token::LBracket {
                self.bump();
                let idx = self.parse_expr()?;
                self.expect(Token::RBracket)?;
                e = Expr::Index(Box::new(e), Box::new(idx));
            } else {
                break;
            }
        }
        Ok(e)
    }

    fn parse_primary(&mut self) -> OResult<Expr> {
        match self.cur().clone() {
            Token::Int(n) => {
                self.bump();
                Ok(Expr::Int(n))
            }
            Token::Float(n) => {
                self.bump();
                Ok(Expr::Float(n))
            }
            Token::KwTrue => {
                self.bump();
                Ok(Expr::Bool(true))
            }
            Token::KwFalse => {
                self.bump();
                Ok(Expr::Bool(false))
            }
            Token::Str(s) => {
                self.bump();
                Ok(Expr::Str(s))
            }
            Token::LParen => {
                self.bump();
                let e = self.parse_expr()?;
                self.expect(Token::RParen)?;
                Ok(e)
            }
            Token::Ident(name) if name == "tensor" => {
                self.bump();
                self.expect(Token::LParen)?;
                let node = self.parse_tensor_lit_node()?;
                self.expect(Token::RParen)?;
                Ok(Expr::TensorLit(node))
            }
            Token::Ident(_) => {
                // possibly-qualified name: foo, or module::foo
                let mut name = self.expect_ident()?;
                while *self.cur() == Token::ColonColon {
                    self.bump();
                    let next = self.expect_ident()?;
                    name.push_str("::");
                    name.push_str(&next);
                }
                if *self.cur() == Token::LParen {
                    self.bump();
                    let mut args = Vec::new();
                    while *self.cur() != Token::RParen {
                        args.push(self.parse_expr()?);
                        if *self.cur() == Token::Comma {
                            self.bump();
                        } else {
                            break;
                        }
                    }
                    self.expect(Token::RParen)?;
                    Ok(Expr::Call(name, args))
                } else {
                    Ok(Expr::Ident(name))
                }
            }
            other => Err(self.err(format!("unexpected token {:?} in expression", other))),
        }
    }

    fn parse_tensor_lit_node(&mut self) -> OResult<TensorLitNode> {
        match self.cur().clone() {
            Token::LBracket => {
                self.bump();
                let mut items = Vec::new();
                while *self.cur() != Token::RBracket {
                    items.push(self.parse_tensor_lit_node()?);
                    if *self.cur() == Token::Comma {
                        self.bump();
                    } else {
                        break;
                    }
                }
                self.expect(Token::RBracket)?;
                Ok(TensorLitNode::List(items))
            }
            Token::Int(n) => {
                self.bump();
                Ok(TensorLitNode::Scalar(n as f64))
            }
            Token::Float(n) => {
                self.bump();
                Ok(TensorLitNode::Scalar(n))
            }
            Token::Minus => {
                self.bump();
                match self.bump() {
                    Token::Int(n) => Ok(TensorLitNode::Scalar(-(n as f64))),
                    Token::Float(n) => Ok(TensorLitNode::Scalar(-n)),
                    other => Err(self.err(format!("expected number after '-', found {:?}", other))),
                }
            }
            other => Err(self.err(format!(
                "expected a number or nested list inside tensor(...), found {:?}",
                other
            ))),
        }
    }
}
