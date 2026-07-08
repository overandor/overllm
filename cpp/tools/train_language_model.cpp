// Real transformer learning experiment: trains OverLLM's C++ transformer
// (cpp/src/model.cpp) as a next-token language model on real tokenized
// text, and reports the loss trajectory so it can be mechanically verified
// to decrease - not just that forward/backward/AdamW "complete without
// crashing" (which cpp/test_overllm.cpp already checked) and not just that
// train_online.cpp's DPO loop runs for N steps on uniformly random token
// pairs (which has no learnable signal by construction: chosen/rejected are
// both random draws from the same distribution, so there is nothing for
// gradient descent to find).
//
// This uses real text (tokenized with the real trained BPE tokenizer from
// tools/bpe_tokenizer.py) and a real training objective (next-token
// cross-entropy via overllm_forward/overllm_backward's public API), and
// prints per-epoch average loss to stdout/JSON so the result is checkable.
//
// Scope honesty: the corpus is small (repeats a handful of real sentences
// from benchmark/rstf/corpus.json) and the model is small (d_model=64,
// 2 layers) so this trains in seconds on CPU. Loss decreasing here proves
// the optimizer and backward pass genuinely do gradient descent on real
// data - it is a memorization/overfitting demonstration on a tiny corpus,
// not a claim of general language understanding.

#include "overllm.h"
#include "tokenizer.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {

// Numerically stable softmax + cross-entropy gradient: dlogits = softmax(logits);
// dlogits[target] -= 1. Returns the cross-entropy loss for reporting.
float softmax_cross_entropy_grad(const std::vector<float>& logits, int target,
                                  std::vector<float>& dlogits) {
    int vocab_size = static_cast<int>(logits.size());
    float max_logit = *std::max_element(logits.begin(), logits.end());
    dlogits.resize(vocab_size);
    double sum_exp = 0.0;
    for (int i = 0; i < vocab_size; ++i) {
        dlogits[i] = std::exp(logits[i] - max_logit);
        sum_exp += dlogits[i];
    }
    for (int i = 0; i < vocab_size; ++i) {
        dlogits[i] = static_cast<float>(dlogits[i] / sum_exp);
    }
    float loss = -std::log(std::max(dlogits[target], 1e-9f));
    dlogits[target] -= 1.0f;
    return loss;
}

std::vector<std::string> load_corpus_sentences(const std::string& path) {
    // benchmark/rstf/corpus.json has a top-level "sentences" array of plain
    // strings; avoid pulling in a JSON library for this one-off tool by
    // parsing the simple, known-flat format directly.
    std::ifstream f(path);
    std::stringstream ss;
    ss << f.rdbuf();
    std::string content = ss.str();

    std::vector<std::string> sentences;
    size_t pos = content.find("\"sentences\"");
    if (pos == std::string::npos) return sentences;
    pos = content.find('[', pos);
    size_t end = content.find(']', pos);
    std::string array_text = content.substr(pos + 1, end - pos - 1);

    size_t i = 0;
    while (i < array_text.size()) {
        size_t start_quote = array_text.find('"', i);
        if (start_quote == std::string::npos) break;
        size_t close_quote = start_quote + 1;
        std::string value;
        while (close_quote < array_text.size() && array_text[close_quote] != '"') {
            if (array_text[close_quote] == '\\' && close_quote + 1 < array_text.size()) {
                value.push_back(array_text[close_quote + 1]);
                close_quote += 2;
            } else {
                value.push_back(array_text[close_quote]);
                close_quote += 1;
            }
        }
        sentences.push_back(value);
        i = close_quote + 1;
    }
    return sentences;
}

}  // namespace

int main(int argc, char** argv) {
    std::string vocab_dir = "cpp/tokenizer_data";
    std::string corpus_path = "benchmark/rstf/corpus.json";
    int epochs = 30;
    int context_window = 24;
    int sentence_limit = 6;
    std::string out_json;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--vocab-dir" && i + 1 < argc) vocab_dir = argv[++i];
        else if (arg == "--corpus" && i + 1 < argc) corpus_path = argv[++i];
        else if (arg == "--epochs" && i + 1 < argc) epochs = std::stoi(argv[++i]);
        else if (arg == "--context-window" && i + 1 < argc) context_window = std::stoi(argv[++i]);
        else if (arg == "--sentence-limit" && i + 1 < argc) sentence_limit = std::stoi(argv[++i]);
        else if (arg == "--out-json" && i + 1 < argc) out_json = argv[++i];
    }

    overllm::BPETokenizer tokenizer;
    if (!tokenizer.load(vocab_dir)) {
        std::cerr << "Failed to load tokenizer from " << vocab_dir << std::endl;
        return 1;
    }

    auto sentences = load_corpus_sentences(corpus_path);
    if (sentences.empty()) {
        std::cerr << "No sentences loaded from " << corpus_path << std::endl;
        return 1;
    }
    if (static_cast<int>(sentences.size()) > sentence_limit) {
        sentences.resize(sentence_limit);
    }

    std::vector<int> corpus_tokens;
    for (const auto& sentence : sentences) {
        auto ids = tokenizer.encode(sentence);
        corpus_tokens.insert(corpus_tokens.end(), ids.begin(), ids.end());
    }
    std::cout << "Corpus: " << sentences.size() << " sentences, "
              << corpus_tokens.size() << " tokens, vocab_size=" << tokenizer.get_vocab_size()
              << std::endl;

    OverLLMConfig cfg = overllm_default_config();
    cfg.vocab_size = tokenizer.get_vocab_size();
    cfg.d_model = 64;
    cfg.n_heads = 4;
    cfg.n_layers = 2;
    cfg.d_ff = 128;
    cfg.max_seq_len = context_window + 1;

    OverLLMModel* model = overllm_load_model("", &cfg);

    std::vector<float> logits(cfg.vocab_size);
    std::vector<float> dlogits(cfg.vocab_size);
    std::vector<float> epoch_losses;

    for (int epoch = 0; epoch < epochs; ++epoch) {
        double epoch_loss_sum = 0.0;
        int steps = 0;

        for (size_t target_pos = 1; target_pos < corpus_tokens.size(); ++target_pos) {
            size_t start = target_pos > static_cast<size_t>(context_window)
                ? target_pos - context_window : 0;
            std::vector<int> prefix(corpus_tokens.begin() + start, corpus_tokens.begin() + target_pos);
            int target = corpus_tokens[target_pos];

            overllm_zero_grad(model);
            overllm_forward(model, prefix.data(), static_cast<int>(prefix.size()), logits.data());
            float loss = softmax_cross_entropy_grad(logits, target, dlogits);
            overllm_backward(model, prefix.data(), static_cast<int>(prefix.size()), dlogits.data());
            overllm_clip_gradients(model, 1.0f);
            overllm_adamw_step(model, 0.001f, 0.9f, 0.999f, 1e-8f, 0.0f);

            epoch_loss_sum += loss;
            ++steps;
        }

        float avg_loss = static_cast<float>(epoch_loss_sum / steps);
        epoch_losses.push_back(avg_loss);
        std::cout << "Epoch " << epoch << " | avg cross-entropy loss: " << avg_loss << std::endl;
    }

    float first_loss = epoch_losses.front();
    float last_loss = epoch_losses.back();
    std::cout << "\nFirst epoch loss: " << first_loss << " | Last epoch loss: " << last_loss
              << " | Reduction: " << (1.0f - last_loss / first_loss) * 100.0f << "%" << std::endl;

    if (!out_json.empty()) {
        std::ofstream out(out_json);
        out << "{\n";
        out << "  \"corpus_sentences\": " << sentences.size() << ",\n";
        out << "  \"corpus_tokens\": " << corpus_tokens.size() << ",\n";
        out << "  \"vocab_size\": " << cfg.vocab_size << ",\n";
        out << "  \"d_model\": " << cfg.d_model << ",\n";
        out << "  \"n_layers\": " << cfg.n_layers << ",\n";
        out << "  \"epochs\": " << epochs << ",\n";
        out << "  \"context_window\": " << context_window << ",\n";
        out << "  \"epoch_losses\": [";
        for (size_t i = 0; i < epoch_losses.size(); ++i) {
            if (i) out << ", ";
            out << epoch_losses[i];
        }
        out << "],\n";
        out << "  \"first_epoch_loss\": " << first_loss << ",\n";
        out << "  \"last_epoch_loss\": " << last_loss << ",\n";
        out << "  \"loss_reduction_ratio\": " << (1.0f - last_loss / first_loss) << "\n";
        out << "}\n";
    }

    overllm_free_model(model);
    return 0;
}
