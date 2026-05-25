#ifndef LLM_CLIENT_H
#define LLM_CLIENT_H

#include <string>
#include <vector>

namespace overllm {

class LocalLLMClient {
public:
    LocalLLMClient(const std::string& host = "http://localhost:11434", 
                   const std::string& model = "llama3.2:latest");
    ~LocalLLMClient();
    
    // Generate text from another local LLM
    std::string generate(const std::string& prompt, 
                        const std::string& system_context = "",
                        float temperature = 0.7f,
                        int max_tokens = 256);
    
    // Generate multiple completions for DPO training
    std::vector<std::string> generate_with_punishment(const std::string& prompt);
    std::vector<std::string> generate_with_reward(const std::string& prompt,
                                                   const std::string& context);
    
    // Check if the LLM is available
    bool is_available();
    
    // Set model
    void set_model(const std::string& model);

private:
    std::string host_;
    std::string model_;

    // HTTP request helper
    std::string http_post(const std::string& endpoint, const std::string& json_body);

    // JSON escaping helper
    static std::string escape_json(const std::string& s);
};

} // namespace overllm

#endif // LLM_CLIENT_H
