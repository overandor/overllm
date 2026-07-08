import Foundation

enum MessageSenderError: Error, CustomStringConvertible {
    case compileFailed(String)
    case executionFailed(String)

    var description: String {
        switch self {
        case .compileFailed(let message): return "AppleScript compile failed: \(message)"
        case .executionFailed(let message): return "AppleScript execution failed: \(message)"
        }
    }
}

/// Sends replies through Messages.app using NSAppleScript — the native
/// Cocoa scripting bridge compiled into this binary — rather than shelling
/// out to the `osascript` CLI or routing through a third-party bridge
/// server. Requires Automation permission for Messages.app to be granted
/// to this binary (System Settings > Privacy & Security > Automation),
/// which macOS will prompt for on first send.
struct MessageSender {

    /// Sends `text` to the 1:1 iMessage buddy identified by `handle`
    /// (a phone number or email, exactly as stored in chat.db's
    /// `handle.id` column).
    func sendToBuddy(handle: String, text: String) throws {
        let script = """
        tell application "Messages"
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "\(MessageSender.escape(handle))" of targetService
            send "\(MessageSender.escape(text))" to targetBuddy
        end tell
        """
        try MessageSender.run(script)
    }

    /// Best-effort send to an existing group chat by its chat.db `guid`.
    /// Group-chat AppleScript addressing is less consistent across macOS
    /// versions than 1:1 buddy sends — verify manually before relying on
    /// this path, and it's only reached when group auto-reply is enabled.
    func sendToChat(chatGUID: String, text: String) throws {
        let script = """
        tell application "Messages"
            set targetChat to a reference to chat id "\(MessageSender.escape(chatGUID))"
            send "\(MessageSender.escape(text))" to targetChat
        end tell
        """
        try MessageSender.run(script)
    }

    private static func run(_ source: String) throws {
        guard let script = NSAppleScript(source: source) else {
            throw MessageSenderError.compileFailed("could not construct NSAppleScript")
        }
        var errorInfo: NSDictionary?
        script.executeAndReturnError(&errorInfo)
        if let errorInfo {
            throw MessageSenderError.executionFailed(errorInfo.description)
        }
    }

    /// Escapes a value for safe interpolation into an AppleScript string
    /// literal (backslash and double-quote are the only two characters
    /// AppleScript string literals treat specially).
    private static func escape(_ s: String) -> String {
        s.replacingOccurrences(of: "\\", with: "\\\\")
         .replacingOccurrences(of: "\"", with: "\\\"")
    }
}
