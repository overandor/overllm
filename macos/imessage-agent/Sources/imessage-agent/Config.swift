import Foundation

/// Runtime configuration, entirely environment-variable driven so the agent
/// can be launched from a LaunchAgent plist without a separate config file.
struct Config {
    var ollamaHost: String
    var ollamaModel: String
    var systemPrompt: String
    var pollIntervalSeconds: Double
    var allowGroupChats: Bool
    var maxReplyChars: Int
    var cooldownSeconds: Double
    var stateFilePath: String
    var chatDBPath: String

    static func fromEnvironment() -> Config {
        let env = ProcessInfo.processInfo.environment
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        return Config(
            ollamaHost: env["OLLAMA_HOST"] ?? "http://localhost:11434",
            ollamaModel: env["OLLAMA_MODEL"] ?? "llama3.2:latest",
            systemPrompt: env["OVERLLM_IMESSAGE_SYSTEM_PROMPT"] ?? Config.defaultSystemPrompt,
            pollIntervalSeconds: Double(env["OVERLLM_IMESSAGE_POLL_SECONDS"] ?? "") ?? 3.0,
            allowGroupChats: (env["OVERLLM_IMESSAGE_ALLOW_GROUPS"] ?? "false").lowercased() == "true",
            maxReplyChars: Int(env["OVERLLM_IMESSAGE_MAX_REPLY_CHARS"] ?? "") ?? 480,
            cooldownSeconds: Double(env["OVERLLM_IMESSAGE_COOLDOWN_SECONDS"] ?? "") ?? 5.0,
            stateFilePath: env["OVERLLM_IMESSAGE_STATE_PATH"] ?? "\(home)/.overllm/data/imessage_state.json",
            chatDBPath: env["OVERLLM_IMESSAGE_CHATDB_PATH"] ?? "\(home)/Library/Messages/chat.db"
        )
    }

    static let defaultSystemPrompt = """
    You are auto-replying to an iMessage on the user's behalf. Keep replies short \
    (1-3 sentences), casual, and in the user's voice. Never reveal you are an AI \
    unless directly asked. Never share passwords, financial details, addresses, \
    or other sensitive personal information.
    """
}
