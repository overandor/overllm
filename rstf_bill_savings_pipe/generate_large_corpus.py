#!/usr/bin/env python3
"""Generate large diverse test corpus for RSTF benchmarking.

Generates 1000+ examples across multiple categories:
- Normal text (baseline)
- Adversarial Unicode (homoglyphs, upside-down, bidi)
- International text (Cyrillic, Greek, Arabic, Chinese)
- Mixed content (text + code + markup)
- Edge cases (very long, very short, special characters)
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Any

# Sample data for generation
NORMAL_TEXT_SAMPLES = [
    "The quick brown fox jumps over the lazy dog.",
    "Hello world, this is a test.",
    "Artificial intelligence is transforming industries.",
    "Machine learning models require large datasets.",
    "Cloud computing enables scalable infrastructure.",
    "Cybersecurity is critical for modern businesses.",
    "Data science combines statistics and programming.",
    "Software engineering requires systematic approaches.",
    "User experience design focuses on customer needs.",
    "Product management balances technical and business goals.",
]

ADVERSARIAL_PATTERNS = [
    ("upside_down", "ʇsǝʇ"),
    ("upside_down", "ʇɥıs ıs ɐ ʇǝsʇ"),
    ("upside_down", "˙ƃop ʎzɐl ǝɥʇ ɹǝʌo sduɯɾ xoɟ uʍoɹq ʞɔᴉnb ǝɥ⊥"),
    ("homoglyph", "Аpple"),
    ("homoglyph", "Вanana"),
    ("homoglyph", "Сherry"),
    ("homoglyph", "Тomato"),
    ("homoglyph", "Хray"),
    ("homoglyph", "Уellow"),
    ("homoglyph", "Тhе qüıck Ьrown fox"),
    ("homoglyph", "сusʈomеr sеrviсе"),
    ("homoglyph", "рroduсt mаnаgеmеnt"),
    ("homoglyph", "sоftwаrе еnginееring"),
    ("bidi", "\u202Btest\u202C"),
    ("bidi", "\u202Bhello world\u202C"),
    ("zero_width", "te\u200Bst"),
    ("zero_width", "hel\u200Blo\u200B wo\u200Brld"),
]

INTERNATIONAL_SAMPLES = {
    "cyrillic": [
        "Привет мир",
        "Искусственный интеллект",
        "Машинное обучение",
        "Кибербезопасность",
        "Облачные вычисления",
    ],
    "greek": [
        "Γεια σου κόσμε",
        "Τεχνητή νοημοσύνη",
        "Μηχανική μάθηση",
        "Κυβερνοασφάλεια",
        "Υπολογιστικά νέφη",
    ],
    "arabic": [
        "مرحبا بالعالم",
        "الذكاء الاصطناعي",
        "التعلم الآلي",
        "الأمن السيبراني",
        "الحوسبة السحابية",
    ],
    "chinese": [
        "你好世界",
        "人工智能",
        "机器学习",
        "网络安全",
        "云计算",
    ],
}

CODE_SAMPLES = [
    "function test() { return true; }",
    "def hello_world(): print('Hello, World!')",
    "const x = 42;",
    "import numpy as np",
    "SELECT * FROM users;",
    "git commit -m 'Initial commit'",
    "docker run -it ubuntu",
    "npm install package",
    "pip install -r requirements.txt",
    "curl https://api.example.com",
]

EDGE_CASES = [
    ("very_short", "a"),
    ("very_short", "ab"),
    ("very_short", "abc"),
    ("very_long", "a" * 1000),
    ("very_long", "test " * 100),
    ("special_chars", "!@#$%^&*()"),
    ("special_chars", "~`-_=+[]{}|;:',.<>?/"),
    ("unicode_emoji", "😀🎉🚀"),
    ("unicode_emoji", "👍👎❤️💔"),
    ("mixed_case", "MiXeD CaSe TeSt"),
    ("numbers", "1234567890"),
    ("mixed_alphanumeric", "test123TEST456"),
]

def generate_example(example_id: int, category: str, text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate a single example."""
    return {
        "id": f"{category}_{example_id}",
        "category": category,
        "text": text,
        "metadata": metadata or {},
    }

def generate_corpus(total_examples: int = 1000) -> List[Dict[str, Any]]:
    """Generate large diverse test corpus."""
    corpus = []
    example_id = 0
    
    # Distribution: 70% normal, 20% adversarial, 10% edge cases
    normal_count = int(total_examples * 0.7)
    adversarial_count = int(total_examples * 0.2)
    international_count = int(total_examples * 0.05)
    code_count = int(total_examples * 0.03)
    edge_count = total_examples - normal_count - adversarial_count - international_count - code_count
    
    print(f"Generating corpus with {total_examples} examples:")
    print(f"  Normal text: {normal_count}")
    print(f"  Adversarial: {adversarial_count}")
    print(f"  International: {international_count}")
    print(f"  Code: {code_count}")
    print(f"  Edge cases: {edge_count}")
    
    # Generate normal text examples
    for i in range(normal_count):
        text = random.choice(NORMAL_TEXT_SAMPLES)
        # Add variations
        if random.random() < 0.3:
            text = text + " " + random.choice(NORMAL_TEXT_SAMPLES)
        if random.random() < 0.2:
            text = text + " " + random.choice(NORMAL_TEXT_SAMPLES) + " " + random.choice(NORMAL_TEXT_SAMPLES)
        
        corpus.append(generate_example(
            example_id,
            "normal",
            text,
            {"variation": "random"}
        ))
        example_id += 1
    
    # Generate adversarial examples
    for i in range(adversarial_count):
        pattern_type, pattern = random.choice(ADVERSARIAL_PATTERNS)
        corpus.append(generate_example(
            example_id,
            "adversarial",
            pattern,
            {"pattern_type": pattern_type}
        ))
        example_id += 1
    
    # Generate international examples
    for i in range(international_count):
        lang = random.choice(list(INTERNATIONAL_SAMPLES.keys()))
        text = random.choice(INTERNATIONAL_SAMPLES[lang])
        corpus.append(generate_example(
            example_id,
            "international",
            text,
            {"language": lang}
        ))
        example_id += 1
    
    # Generate code examples
    for i in range(code_count):
        text = random.choice(CODE_SAMPLES)
        if random.random() < 0.3:
            text = text + "\n" + random.choice(CODE_SAMPLES)
        corpus.append(generate_example(
            example_id,
            "code",
            text,
            {"language": "programming"}
        ))
        example_id += 1
    
    # Generate edge case examples
    for i in range(edge_count):
        case_type, text = random.choice(EDGE_CASES)
        corpus.append(generate_example(
            example_id,
            "edge_case",
            text,
            {"case_type": case_type}
        ))
        example_id += 1
    
    # Shuffle corpus
    random.shuffle(corpus)
    
    # Reassign IDs after shuffle
    for i, example in enumerate(corpus):
        example["id"] = f"{example['category']}_{i}"
    
    return corpus

def save_corpus(corpus: List[Dict[str, Any]], output_path: Path):
    """Save corpus to JSONL file."""
    with output_path.open("w", encoding="utf-8") as f:
        for example in corpus:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
    print(f"Saved {len(corpus)} examples to {output_path}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate large diverse test corpus")
    parser.add_argument("--count", type=int, default=1000, help="Number of examples to generate")
    parser.add_argument("--output", type=Path, default=Path("large_corpus.jsonl"), help="Output file path")
    args = parser.parse_args()
    
    corpus = generate_corpus(args.count)
    save_corpus(corpus, args.output)
    
    # Print statistics
    categories = {}
    for example in corpus:
        cat = example["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\nCorpus statistics:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} ({count/len(corpus)*100:.1f}%)")

if __name__ == "__main__":
    main()
