#include "llm_client.h"
#include "tokenizer.h"
#include <iostream>
#include <vector>

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "  Local LLM Client Test" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;

    overllm::LocalLLMClient client("http://localhost:11434", "llama3.2:latest");

    // Check if LLM is available
    std::cout << "Checking if LLM is available..." << std::endl;
    if (client.is_available()) {
        std::cout << "✓ LLM is available" << std::endl;
    } else {
        std::cout << "❌ LLM is not available (make sure Ollama is running)" << std::endl;
        std::cout << "   Start Ollama with: ollama serve" << std::endl;
        std::cout << "   Pull model with: ollama pull llama3.2" << std::endl;
        return 1;
    }
    std::cout << std::endl;

    // Test basic generation
    std::cout << "Testing basic generation..." << std::endl;
    std::string prompt = "What is the capital of France?";
    std::string response = client.generate(prompt, "", 0.7f, 128);
    
    if (!response.empty()) {
        std::cout << "✓ Generation successful" << std::endl;
        std::cout << "  Prompt: " << prompt << std::endl;
        std::cout << "  Response: " << response << std::endl;
    } else {
        std::cout << "❌ Generation failed" << std::endl;
    }
    std::cout << std::endl;

    // Test with system context
    std::cout << "Testing generation with system context..." << std::endl;
    std::string context = "You are a helpful assistant.";
    std::string response_with_ctx = client.generate("Say hello", context, 0.7f, 64);
    
    if (!response_with_ctx.empty()) {
        std::cout << "✓ Generation with context successful" << std::endl;
        std::cout << "  Response: " << response_with_ctx << std::endl;
    } else {
        std::cout << "❌ Generation with context failed" << std::endl;
    }
    std::cout << std::endl;

    // Test punishment generation (for DPO)
    std::cout << "Testing punishment generation (for DPO)..." << std::endl;
    std::vector<std::string> punished = client.generate_with_punishment("Write a bad response");
    if (!punished.empty()) {
        std::cout << "✓ Punishment generation successful" << std::endl;
        std::cout << "  Response: " << punished[0] << std::endl;
    } else {
        std::cout << "❌ Punishment generation failed" << std::endl;
    }
    std::cout << std::endl;

    // Test reward generation (for DPO)
    std::cout << "Testing reward generation (for DPO)..." << std::endl;
    std::vector<std::string> rewarded = client.generate_with_reward("Write a good response", "Be helpful and concise.");
    if (!rewarded.empty()) {
        std::cout << "✓ Reward generation successful" << std::endl;
        std::cout << "  Response: " << rewarded[0] << std::endl;
    } else {
        std::cout << "❌ Reward generation failed" << std::endl;
    }
    std::cout << std::endl;

    // Test tokenizer integration
    std::cout << "Testing tokenizer integration..." << std::endl;
    overllm::BPETokenizer tokenizer;
    if (tokenizer.load("vocab.txt")) {
        std::string test_text = "hello world";
        std::vector<int> tokens = tokenizer.encode(test_text);
        std::cout << "✓ Tokenizer loaded" << std::endl;
        std::cout << "  Text: " << test_text << std::endl;
        std::cout << "  Tokens: ";
        for (size_t i = 0; i < std::min(tokens.size(), (size_t)10); ++i) {
            std::cout << tokens[i] << " ";
        }
        std::cout << std::endl;
    } else {
        std::cout << "⚠ Tokenizer not available" << std::endl;
    }
    std::cout << std::endl;

    std::cout << "========================================" << std::endl;
    std::cout << "  Test Complete" << std::endl;
    std::cout << "========================================" << std::endl;

    return 0;
}
