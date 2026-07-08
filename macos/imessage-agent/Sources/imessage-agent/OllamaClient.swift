import Foundation

enum OllamaError: Error, CustomStringConvertible {
    case invalidHost(String)
    case badResponse(Int)

    var description: String {
        switch self {
        case .invalidHost(let host): return "invalid Ollama host: \(host)"
        case .badResponse(let status): return "Ollama returned HTTP \(status)"
        }
    }
}

/// Native URLSession client for Ollama's /api/generate endpoint, mirroring
/// the request/response contract used by cpp/src/llm_client.cpp so both
/// clients talk to the same Ollama server the same way.
struct OllamaClient {
    let host: String
    let model: String

    private struct GenerateRequest: Encodable {
        let model: String
        let prompt: String
        let stream: Bool
        let options: Options

        struct Options: Encodable {
            let temperature: Double
            let num_predict: Int
        }
    }

    private struct GenerateResponse: Decodable {
        let response: String
    }

    func generate(prompt: String, systemContext: String, temperature: Double = 0.7, maxTokens: Int = 200) async throws -> String {
        var fullPrompt = prompt
        if !systemContext.isEmpty {
            fullPrompt = "[SYSTEM CONTEXT]\n\(systemContext)\n[/SYSTEM CONTEXT]\n\n\(prompt)"
        }

        guard let url = URL(string: "\(host)/api/generate") else {
            throw OllamaError.invalidHost(host)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(GenerateRequest(
            model: model,
            prompt: fullPrompt,
            stream: false,
            options: .init(temperature: temperature, num_predict: maxTokens)
        ))

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            let status = (response as? HTTPURLResponse)?.statusCode ?? -1
            throw OllamaError.badResponse(status)
        }
        let decoded = try JSONDecoder().decode(GenerateResponse.self, from: data)
        return decoded.response.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
