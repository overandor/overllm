import Foundation

/// Persisted across restarts so the agent never replays message history it
/// already handled, and never rapid-fires replies at the same sender
/// (important if the other side is also a bot — without a cooldown two
/// auto-reply agents can loop indefinitely).
struct ReplyState: Codable {
    var lastProcessedRowID: Int64
    var lastReplyBySender: [String: Date]

    static func load(path: String) -> ReplyState {
        guard let data = FileManager.default.contents(atPath: path),
              let decoded = try? JSONDecoder().decode(ReplyState.self, from: data) else {
            return ReplyState(lastProcessedRowID: 0, lastReplyBySender: [:])
        }
        return decoded
    }

    func save(path: String) {
        let dir = (path as NSString).deletingLastPathComponent
        try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
        guard let data = try? JSONEncoder().encode(self) else { return }
        try? data.write(to: URL(fileURLWithPath: path), options: .atomic)
    }
}
