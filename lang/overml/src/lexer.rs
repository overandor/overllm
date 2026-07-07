//! Hand-written lexer. No regex/logos dependency on purpose — OverML's whole
//! pitch is a small, auditable toolchain, so the front end stays a plain
//! character scanner.

use crate::error::{OResult, OverMlError};

#[derive(Debug, Clone, PartialEq)]
pub enum Token {
    Ident(String),
    Int(i64),
    Float(f64),
    Str(String),

    KwLet,
    KwFn,
    KwReturn,
    KwIf,
    KwElse,
    KwWhile,
    KwTrue,
    KwFalse,
    KwImport,
    KwPrint,

    LParen,
    RParen,
    LBrace,
    RBrace,
    LBracket,
    RBracket,
    Comma,
    Colon,
    ColonColon,
    Semi,
    Arrow,
    Eq,
    EqEq,
    NotEq,
    Lt,
    Gt,
    Le,
    Ge,
    Plus,
    Minus,
    Star,
    Slash,
    At,
    Bang,
    AndAnd,
    OrOr,

    Eof,
}

#[derive(Debug, Clone)]
pub struct Spanned {
    pub tok: Token,
    pub line: usize,
    pub col: usize,
}

pub struct Lexer {
    chars: Vec<char>,
    pos: usize,
    line: usize,
    col: usize,
}

impl Lexer {
    pub fn new(src: &str) -> Self {
        Lexer {
            chars: src.chars().collect(),
            pos: 0,
            line: 1,
            col: 1,
        }
    }

    fn peek(&self) -> Option<char> {
        self.chars.get(self.pos).copied()
    }

    fn peek2(&self) -> Option<char> {
        self.chars.get(self.pos + 1).copied()
    }

    fn advance(&mut self) -> Option<char> {
        let c = self.peek()?;
        self.pos += 1;
        if c == '\n' {
            self.line += 1;
            self.col = 1;
        } else {
            self.col += 1;
        }
        Some(c)
    }

    pub fn tokenize(mut self) -> OResult<Vec<Spanned>> {
        let mut out = Vec::new();
        loop {
            self.skip_trivia();
            let (line, col) = (self.line, self.col);
            let Some(c) = self.peek() else {
                out.push(Spanned {
                    tok: Token::Eof,
                    line,
                    col,
                });
                break;
            };

            let tok = if c.is_ascii_digit() {
                self.lex_number()?
            } else if c == '"' {
                self.lex_string()?
            } else if is_ident_start(c) {
                self.lex_ident_or_kw()
            } else {
                self.lex_punct()?
            };
            out.push(Spanned { tok, line, col });
        }
        Ok(out)
    }

    fn skip_trivia(&mut self) {
        loop {
            match self.peek() {
                Some(c) if c.is_whitespace() => {
                    self.advance();
                }
                Some('/') if self.peek2() == Some('/') => {
                    while let Some(c) = self.peek() {
                        if c == '\n' {
                            break;
                        }
                        self.advance();
                    }
                }
                _ => break,
            }
        }
    }

    fn lex_number(&mut self) -> OResult<Token> {
        let start = self.pos;
        let (line, col) = (self.line, self.col);
        let mut is_float = false;
        while let Some(c) = self.peek() {
            if c.is_ascii_digit() {
                self.advance();
            } else if c == '.' && !is_float && self.peek2().map(|c| c.is_ascii_digit()).unwrap_or(false) {
                is_float = true;
                self.advance();
            } else {
                break;
            }
        }
        let text: String = self.chars[start..self.pos].iter().collect();
        if is_float {
            text.parse::<f64>()
                .map(Token::Float)
                .map_err(|_| OverMlError::new(format!("invalid float literal '{}'", text), line, col))
        } else {
            text.parse::<i64>()
                .map(Token::Int)
                .map_err(|_| OverMlError::new(format!("invalid integer literal '{}'", text), line, col))
        }
    }

    fn lex_string(&mut self) -> OResult<Token> {
        let (line, col) = (self.line, self.col);
        self.advance(); // opening quote
        let mut s = String::new();
        loop {
            match self.advance() {
                None => return Err(OverMlError::new("unterminated string literal", line, col)),
                Some('"') => break,
                Some('\\') => match self.advance() {
                    Some('n') => s.push('\n'),
                    Some('t') => s.push('\t'),
                    Some('"') => s.push('"'),
                    Some('\\') => s.push('\\'),
                    Some(other) => s.push(other),
                    None => return Err(OverMlError::new("unterminated escape in string literal", line, col)),
                },
                Some(c) => s.push(c),
            }
        }
        Ok(Token::Str(s))
    }

    fn lex_ident_or_kw(&mut self) -> Token {
        let start = self.pos;
        while let Some(c) = self.peek() {
            if is_ident_continue(c) {
                self.advance();
            } else {
                break;
            }
        }
        let text: String = self.chars[start..self.pos].iter().collect();
        match text.as_str() {
            "let" => Token::KwLet,
            "fn" => Token::KwFn,
            "return" => Token::KwReturn,
            "if" => Token::KwIf,
            "else" => Token::KwElse,
            "while" => Token::KwWhile,
            "true" => Token::KwTrue,
            "false" => Token::KwFalse,
            "import" => Token::KwImport,
            "print" => Token::KwPrint,
            _ => Token::Ident(text),
        }
    }

    fn lex_punct(&mut self) -> OResult<Token> {
        let (line, col) = (self.line, self.col);
        let c = self.advance().unwrap();
        let tok = match c {
            '(' => Token::LParen,
            ')' => Token::RParen,
            '{' => Token::LBrace,
            '}' => Token::RBrace,
            '[' => Token::LBracket,
            ']' => Token::RBracket,
            ',' => Token::Comma,
            ';' => Token::Semi,
            '@' => Token::At,
            '+' => Token::Plus,
            '-' => {
                if self.peek() == Some('>') {
                    self.advance();
                    Token::Arrow
                } else {
                    Token::Minus
                }
            }
            '*' => Token::Star,
            '/' => Token::Slash,
            ':' => {
                if self.peek() == Some(':') {
                    self.advance();
                    Token::ColonColon
                } else {
                    Token::Colon
                }
            }
            '=' => {
                if self.peek() == Some('=') {
                    self.advance();
                    Token::EqEq
                } else {
                    Token::Eq
                }
            }
            '!' => {
                if self.peek() == Some('=') {
                    self.advance();
                    Token::NotEq
                } else {
                    Token::Bang
                }
            }
            '<' => {
                if self.peek() == Some('=') {
                    self.advance();
                    Token::Le
                } else {
                    Token::Lt
                }
            }
            '>' => {
                if self.peek() == Some('=') {
                    self.advance();
                    Token::Ge
                } else {
                    Token::Gt
                }
            }
            '&' if self.peek() == Some('&') => {
                self.advance();
                Token::AndAnd
            }
            '|' if self.peek() == Some('|') => {
                self.advance();
                Token::OrOr
            }
            other => {
                return Err(OverMlError::new(
                    format!("unexpected character '{}'", other),
                    line,
                    col,
                ))
            }
        };
        Ok(tok)
    }
}

fn is_ident_start(c: char) -> bool {
    c.is_alphabetic() || c == '_'
}

fn is_ident_continue(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}
