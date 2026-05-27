#!/usr/bin/env python3
import argparse
import json
import math
import os
import numpy as np
from pathlib import Path

def softmax(x, axis=-1):
    x = x - np.max(x, axis=axis, keepdims=True)
    e = np.exp(x)
    return e / np.sum(e, axis=axis, keepdims=True)

def gelu(x):
    return x * 0.5 * (1 + np.tanh(0.79788456 * (x + 0.044715 * x**3)))

def layer_norm(x, gamma, beta, eps=1e-5):
    mean = np.mean(x, axis=-1, keepdims=True)
    var = np.var(x, axis=-1, keepdims=True)
    return gamma * (x - mean) / np.sqrt(var + eps) + beta

def causal_mask(seq_len):
    mask = np.triu(np.ones((seq_len, seq_len)), k=1)
    return mask * -1e9

class SimpleTransformer:
    def __init__(self, vocab_size, d_model=64, n_heads=2, n_layers=2, d_ff=128, max_len=128, lr=1e-2):
        self.vocab_size = vocab_size
        self.d = d_model
        self.nh = n_heads
        self.dh = d_model // n_heads
        self.nl = n_layers
        self.d_ff = d_ff
        self.max_len = max_len
        self.lr = lr
        np.random.seed(42)
        self.emb = np.random.randn(vocab_size, d_model).astype(np.float32) * 0.02
        self.pos = np.random.randn(max_len, d_model).astype(np.float32) * 0.02
        self.blocks = []
        for _ in range(n_layers):
            wq = np.random.randn(d_model, d_model).astype(np.float32) * np.sqrt(2.0 / (d_model + d_model))
            wk = np.random.randn(d_model, d_model).astype(np.float32) * np.sqrt(2.0 / (d_model + d_model))
            wv = np.random.randn(d_model, d_model).astype(np.float32) * np.sqrt(2.0 / (d_model + d_model))
            wo = np.random.randn(d_model, d_model).astype(np.float32) * np.sqrt(2.0 / (d_model + d_model))
            bq = np.zeros(d_model, dtype=np.float32)
            bk = np.zeros(d_model, dtype=np.float32)
            bv = np.zeros(d_model, dtype=np.float32)
            bo = np.zeros(d_model, dtype=np.float32)
            w1 = np.random.randn(d_model, d_ff).astype(np.float32) * np.sqrt(2.0 / (d_model + d_ff))
            w2 = np.random.randn(d_ff, d_model).astype(np.float32) * np.sqrt(2.0 / (d_ff + d_model))
            b1 = np.zeros(d_ff, dtype=np.float32)
            b2 = np.zeros(d_model, dtype=np.float32)
            ln1_g = np.ones(d_model, dtype=np.float32)
            ln1_b = np.zeros(d_model, dtype=np.float32)
            ln2_g = np.ones(d_model, dtype=np.float32)
            ln2_b = np.zeros(d_model, dtype=np.float32)
            self.blocks.append({
                'Wq': wq, 'Wk': wk, 'Wv': wv, 'Wo': wo,
                'bq': bq, 'bk': bk, 'bv': bv, 'bo': bo,
                'W1': w1, 'W2': w2, 'b1': b1, 'b2': b2,
                'ln1_g': ln1_g, 'ln1_b': ln1_b, 'ln2_g': ln2_g, 'ln2_b': ln2_b,
            })
        self.ln_f_g = np.ones(d_model, dtype=np.float32)
        self.ln_f_b = np.zeros(d_model, dtype=np.float32)
        self.out_w = np.random.randn(d_model, vocab_size).astype(np.float32) * 0.02
        self.out_b = np.zeros(vocab_size, dtype=np.float32)

    def attention(self, x, blk):
        seq, d = x.shape
        q = x @ blk['Wq'] + blk['bq']
        k = x @ blk['Wk'] + blk['bk']
        v = x @ blk['Wv'] + blk['bv']
        q = q.reshape(seq, self.nh, self.dh).transpose(1, 0, 2)
        k = k.reshape(seq, self.nh, self.dh).transpose(1, 0, 2)
        v = v.reshape(seq, self.nh, self.dh).transpose(1, 0, 2)
        scores = (q @ k.transpose(0, 2, 1)) / np.sqrt(self.dh)
        scores = scores + causal_mask(seq)
        scores = softmax(scores, axis=-1)
        out = scores @ v
        out = out.transpose(1, 0, 2).reshape(seq, d)
        return out @ blk['Wo'] + blk['bo']

    def forward(self, tokens):
        seq = len(tokens)
        # Truncate to max_len if needed
        if seq > self.max_len:
            tokens = tokens[:self.max_len]
            seq = self.max_len
        x = self.emb[tokens] + self.pos[:seq]
        for blk in self.blocks:
            attn_out = self.attention(x, blk)
            x = layer_norm(x + attn_out, blk['ln1_g'], blk['ln1_b'])
            ffn = gelu(x @ blk['W1'] + blk['b1'])
            ffn = ffn @ blk['W2'] + blk['b2']
            x = layer_norm(x + ffn, blk['ln2_g'], blk['ln2_b'])
        x = layer_norm(x, self.ln_f_g, self.ln_f_b)
        logits = x @ self.out_w + self.out_b
        return logits

    def forward_hidden(self, tokens):
        if len(tokens) > self.max_len:
            tokens = tokens[:self.max_len]
        seq = len(tokens)
        x = self.emb[tokens] + self.pos[:seq]
        for blk in self.blocks:
            attn_out = self.attention(x, blk)
            x = layer_norm(x + attn_out, blk['ln1_g'], blk['ln1_b'])
            ffn = gelu(x @ blk['W1'] + blk['b1'])
            ffn = ffn @ blk['W2'] + blk['b2']
            x = layer_norm(x + ffn, blk['ln2_g'], blk['ln2_b'])
        x = layer_norm(x, self.ln_f_g, self.ln_f_b)
        return x

    def log_prob_and_grad(self, tokens):
        if len(tokens) > self.max_len:
            tokens = tokens[:self.max_len]
        hidden = self.forward_hidden(tokens)
        logits = hidden @ self.out_w + self.out_b
        n = len(tokens)
        total_lp = 0.0
        grad_w = np.zeros_like(self.out_w)
        grad_b = np.zeros_like(self.out_b)
        grad_emb = {}
        count = 0
        for i in range(1, n):
            li = logits[i - 1]
            li_max = np.max(li)
            exp_li = np.exp(li - li_max)
            sm = exp_li / np.sum(exp_li)
            target = tokens[i]
            total_lp += np.log(sm[target] + 1e-10)
            count += 1
            dsm = -sm
            dsm[target] += 1.0
            h = hidden[i - 1]
            grad_w += np.outer(h, dsm)
            grad_b += dsm
            grad_h = dsm @ self.out_w.T
            src_tok = tokens[i - 1]
            if src_tok not in grad_emb:
                grad_emb[src_tok] = np.zeros(self.d, dtype=np.float32)
            grad_emb[src_tok] += grad_h
        avg_lp = total_lp / max(count, 1)
        scale = 1.0 / max(count, 1)
        return avg_lp, grad_w * scale, grad_b * scale, grad_emb, scale

    def log_prob(self, tokens):
        lp, _, _, _, _ = self.log_prob_and_grad(tokens)
        return lp

    def dpo_loss(self, chosen, rejected, beta=0.1):
        pi_yw = self.log_prob(chosen)
        pi_yl = self.log_prob(rejected)
        margin = beta * (pi_yw - pi_yl)
        sigmoid = 1.0 / (1.0 + np.exp(-margin))
        loss = -np.log(sigmoid + 1e-10)
        return loss

    def train_step(self, chosen, rejected, beta=0.1):
        lp_c, gw_c, gb_c, ge_c, _ = self.log_prob_and_grad(chosen)
        lp_r, gw_r, gb_r, ge_r, _ = self.log_prob_and_grad(rejected)

        margin = beta * (lp_c - lp_r)
        sigmoid = 1.0 / (1.0 + np.exp(-margin))
        loss = -np.log(sigmoid + 1e-10)
        coeff = self.lr * beta * (1.0 - sigmoid)

        self.out_w += coeff * (gw_c - gw_r)
        self.out_b += coeff * (gb_c - gb_r)

        all_tokens = set(list(ge_c.keys()) + list(ge_r.keys()))
        for t in all_tokens:
            gc = ge_c.get(t, np.zeros(self.d, dtype=np.float32))
            gr = ge_r.get(t, np.zeros(self.d, dtype=np.float32))
            self.emb[t] += coeff * (gc - gr)

        return float(loss)

    def export_to_cpp(self, path):
        with open(path, 'wb') as f:
            def write(arr):
                f.write(arr.astype(np.float32).tobytes())
            write(self.emb)
            write(self.pos)
            for blk in self.blocks:
                write(blk['Wq']); write(blk['bq'])
                write(blk['Wk']); write(blk['bk'])
                write(blk['Wv']); write(blk['bv'])
                write(blk['Wo']); write(blk['bo'])
                write(blk['W1']); write(blk['b1'])
                write(blk['W2']); write(blk['b2'])
                write(blk['ln1_g']); write(blk['ln1_b'])
                write(blk['ln2_g']); write(blk['ln2_b'])
            write(self.ln_f_g); write(self.ln_f_b)
            write(self.out_w); write(self.out_b)
        print(f"Exported weights to {path}")

def simple_tokenizer(text, vocab):
    tokens = [vocab.get('<s>', 2)]
    cur = ""
    for c in text:
        if c in ' \n\t.,!?;:()[]{}\'"':
            if cur:
                tokens.append(vocab.get(cur, vocab.get('<unk>', 1)))
                cur = ""
            if c in vocab:
                tokens.append(vocab[c])
        else:
            cur += c
    if cur:
        tokens.append(vocab.get(cur, vocab.get('<unk>', 1)))
    tokens.append(vocab.get('</s>', 3))
    return tokens

def build_vocab_from_data(data_path, max_vocab_size=10000):
    """Build vocabulary from training data"""
    vocab = {'<pad>': 0, '<unk>': 1, '<s>': 2, '</s>': 3}
    word_counts = {}
    
    if Path(data_path).exists():
        with open(data_path) as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    text = item.get('chosen', '') + ' ' + item.get('rejected', '')
                    # Count words - split by whitespace and common delimiters
                    import re
                    words = re.findall(r'\w+|[^\w\s]', text)
                    for word in words:
                        if len(word) > 0:
                            word_counts[word] = word_counts.get(word, 0) + 1
    
    # Add most common words to vocab
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    for word, count in sorted_words[:max_vocab_size - 4]:
        vocab[word] = len(vocab)
    
    print(f"Built vocabulary with {len(vocab)} tokens from {len(word_counts)} unique words")
    return vocab

def build_vocab(path):
    # Try to build from training data if it's a JSONL file
    if path and Path(path).exists() and path.endswith('.jsonl'):
        return build_vocab_from_data(path)
    
    # Otherwise use simple text file
    vocab = {'<pad>': 0, '<unk>': 1, '<s>': 2, '</s>': 3}
    if path and Path(path).exists():
        for word in Path(path).read_text().split():
            if word not in vocab:
                vocab[word] = len(vocab)
    return vocab

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/preferences.jsonl")
    parser.add_argument("--vocab", default="")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--beta", type=float, default=0.1)
    parser.add_argument("--export", default="models/overllm.bin")
    parser.add_argument("--batch_size", type=int, default=100, help="Batch size for training")
    parser.add_argument("--max_samples", type=int, default=None, help="Limit samples for faster training")
    args = parser.parse_args()
    
    # Build vocabulary from data if no vocab file provided
    if not args.vocab:
        vocab = build_vocab(args.data)
    else:
        vocab = build_vocab(args.vocab)
    
    model = SimpleTransformer(vocab_size=len(vocab), d_model=64, n_heads=2, n_layers=2, d_ff=128)
    pairs = []
    if Path(args.data).exists():
        with open(args.data) as f:
            for line in f:
                if line.strip():
                    pairs.append(json.loads(line))
    
    # Limit samples if specified
    if args.max_samples and len(pairs) > args.max_samples:
        pairs = pairs[:args.max_samples]
        print(f"Limited to {args.max_samples} samples")
    
    print(f"Loaded {len(pairs)} preference pairs")
    print(f"Vocab size: {len(vocab)}")

    metrics_path = Path.home() / ".overllm" / "data" / "training_metrics.json"
    import time, urllib.request

    def push_metrics(data):
        push_url = os.environ.get("OVERLLM_PUSH_URL", "")
        push_key = os.environ.get("OVERLLM_PUSH_KEY", "overllm-local-dev")
        if not push_url:
            return
        try:
            req = urllib.request.Request(
                push_url,
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json", "x-overllm-key": push_key},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print(f"Push failed: {e}")

    # Pre-tokenize all pairs
    print("Pre-tokenizing training pairs...")
    tokenized_pairs = []
    for pair in pairs:
        chosen = simple_tokenizer(pair['chosen'], vocab)
        rejected = simple_tokenizer(pair['rejected'], vocab)
        if len(chosen) > 2 and len(rejected) > 2:
            tokenized_pairs.append((chosen, rejected))
    print(f"Tokenized {len(tokenized_pairs)} valid pairs")

    epoch_history = []
    training_start = time.time()

    for epoch in range(args.epochs):
        total_loss = 0.0
        valid_pairs = 0
        epoch_start = time.time()

        from tqdm import tqdm
        for i in tqdm(range(0, len(tokenized_pairs), args.batch_size),
                      desc=f"Epoch {epoch + 1}/{args.epochs}"):
            batch = tokenized_pairs[i:i+args.batch_size]
            for chosen, rejected in batch:
                loss = model.train_step(chosen, rejected, args.beta)
                total_loss += loss
                valid_pairs += 1

        avg = total_loss / max(valid_pairs, 1)
        epoch_time = time.time() - epoch_start
        print(f"Epoch {epoch + 1}/{args.epochs} | DPO Loss: {avg:.4f} | Valid pairs: {valid_pairs}")

        epoch_history.append({"epoch": epoch + 1, "loss": round(avg, 6), "time_s": round(epoch_time, 1)})
        metrics = {
            "status": "training",
            "current_epoch": epoch + 1,
            "total_epochs": args.epochs,
            "dpo_loss": round(avg, 6),
            "preference_pairs": len(tokenized_pairs),
            "vocab_size": len(vocab),
            "model_params": {"d_model": 64, "n_heads": 2, "n_layers": 2, "d_ff": 128},
            "elapsed_s": round(time.time() - training_start, 1),
            "epoch_history": epoch_history,
            "updated_at": int(time.time()),
        }
        metrics_path.write_text(json.dumps(metrics, indent=2))
        push_metrics(metrics)

        if avg < 0.1:
            print(f"Early stopping: loss {avg:.4f} below threshold")
            break

    metrics["status"] = "complete"
    metrics["updated_at"] = int(time.time())
    metrics_path.write_text(json.dumps(metrics, indent=2))
    push_metrics(metrics)
    
    Path(args.export).parent.mkdir(parents=True, exist_ok=True)
    model.export_to_cpp(args.export)

    vocab_path = str(Path(args.export).parent / "vocab_trained.txt")
    inv_vocab = {v: k for k, v in vocab.items()}
    with open(vocab_path, 'w') as vf:
        for i in range(len(vocab)):
            vf.write(inv_vocab[i] + '\n')
    print(f"Exported vocab to {vocab_path} ({len(vocab)} tokens)")
    print(f"\nTraining complete. Model exported to {args.export}")

if __name__ == "__main__":
    main()
