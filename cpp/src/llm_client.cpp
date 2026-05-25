#include "llm_client.h"
#include <sstream>
#include <fstream>
#include <iostream>
#include <cstring>
#include <cstdlib>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <netdb.h>

namespace overllm {

LocalLLMClient::LocalLLMClient(const std::string& host, const std::string& model)
    : host_(host), model_(model) {
}

LocalLLMClient::~LocalLLMClient() {
}

std::string LocalLLMClient::http_post(const std::string& endpoint, const std::string& json_body) {
    // Parse host to get hostname and port
    std::string hostname = "localhost";
    int port = 11434;
    
    size_t host_start = host_.find("://");
    if (host_start != std::string::npos) {
        host_start += 3;
    } else {
        host_start = 0;
    }
    
    std::string host_part = host_.substr(host_start);
    size_t colon_pos = host_part.find(':');
    if (colon_pos != std::string::npos) {
        hostname = host_part.substr(0, colon_pos);
        port = std::stoi(host_part.substr(colon_pos + 1));
    } else {
        hostname = host_part;
    }
    
    // Create socket
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        return "";
    }
    
    // Connect to server
    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    
    struct hostent* he = gethostbyname(hostname.c_str());
    if (he == nullptr) {
        close(sock);
        return "";
    }
    
    memcpy(&server_addr.sin_addr, he->h_addr_list[0], he->h_length);
    
    if (connect(sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        close(sock);
        return "";
    }
    
    // Build HTTP request
    std::stringstream request;
    request << "POST " << endpoint << " HTTP/1.1\r\n";
    request << "Host: " << hostname << ":" << port << "\r\n";
    request << "Content-Type: application/json\r\n";
    request << "Content-Length: " << json_body.length() << "\r\n";
    request << "Connection: close\r\n";
    request << "\r\n";
    request << json_body;
    
    std::string request_str = request.str();
    
    // Send request
    if (send(sock, request_str.c_str(), request_str.length(), 0) < 0) {
        close(sock);
        return "";
    }
    
    // Read response
    std::string response;
    char buffer[4096];
    int bytes_received;
    while ((bytes_received = recv(sock, buffer, sizeof(buffer) - 1, 0)) > 0) {
        buffer[bytes_received] = '\0';
        response += buffer;
    }
    
    close(sock);
    
    // Extract body from HTTP response
    size_t body_start = response.find("\r\n\r\n");
    if (body_start != std::string::npos) {
        return response.substr(body_start + 4);
    }
    
    return response;
}

std::string LocalLLMClient::generate(const std::string& prompt, 
                                      const std::string& system_context,
                                      float temperature,
                                      int max_tokens) {
    std::string full_prompt = prompt;
    if (!system_context.empty()) {
        full_prompt = "[SYSTEM CONTEXT]\n" + system_context + "\n[/SYSTEM CONTEXT]\n\n" + prompt;
    }
    
    // Build JSON request
    std::stringstream json;
    json << "{";
    json << "\"model\": \"" << model_ << "\",";
    json << "\"prompt\": " << escape_json(full_prompt) << ",";
    json << "\"stream\": false,";
    json << "\"options\": {";
    json << "\"temperature\": " << temperature << ",";
    json << "\"num_predict\": " << max_tokens;
    json << "}";
    json << "}";
    
    std::string response = http_post("/api/generate", json.str());
    
    // Extract "response" field from JSON
    size_t response_key = response.find("\"response\":");
    if (response_key != std::string::npos) {
        size_t value_start = response.find("\"", response_key + 11);
        if (value_start != std::string::npos) {
            value_start++;  // Skip opening quote
            size_t value_end = response.find("\"", value_start);
            if (value_end != std::string::npos) {
                return response.substr(value_start, value_end - value_start);
            }
        }
    }
    
    return "";
}

std::vector<std::string> LocalLLMClient::generate_with_punishment(const std::string& prompt) {
    std::vector<std::string> results;
    std::string response = generate(prompt, "", 0.9f, 256);
    if (!response.empty()) {
        results.push_back(response);
    }
    return results;
}

std::vector<std::string> LocalLLMClient::generate_with_reward(const std::string& prompt,
                                                                const std::string& context) {
    std::vector<std::string> results;
    std::string response = generate(prompt, context, 0.7f, 256);
    if (!response.empty()) {
        results.push_back(response);
    }
    return results;
}

bool LocalLLMClient::is_available() {
    std::string response = http_post("/api/tags", "{}");
    return !response.empty();
}

void LocalLLMClient::set_model(const std::string& model) {
    model_ = model;
}

std::string LocalLLMClient::escape_json(const std::string& s) {
    std::stringstream result;
    result << "\"";
    for (char c : s) {
        switch (c) {
            case '"': result << "\\\""; break;
            case '\\': result << "\\\\"; break;
            case '\n': result << "\\n"; break;
            case '\r': result << "\\r"; break;
            case '\t': result << "\\t"; break;
            default: result << c; break;
        }
    }
    result << "\"";
    return result.str();
}

} // namespace overllm
