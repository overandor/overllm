import Foundation
import SQLite3

/// A single incoming (not sent by the user) iMessage, with enough routing
/// information to send a reply back to the right conversation.
struct IncomingMessage {
    let rowID: Int64
    let guid: String
    let text: String
    let senderHandle: String
    let chatGUID: String
    let chatIdentifier: String
    let isGroupChat: Bool
    let date: Date
}

enum ChatDatabaseError: Error, CustomStringConvertible {
    case openFailed(String)
    case queryFailed(String)

    var description: String {
        switch self {
        case .openFailed(let message): return "failed to open chat.db: \(message)"
        case .queryFailed(let message): return "chat.db query failed: \(message)"
        }
    }
}

/// Reads new messages directly out of Messages.app's SQLite database
/// (~/Library/Messages/chat.db) using the system libsqlite3, opened
/// read-only. Requires the running process to have Full Disk Access
/// (System Settings > Privacy & Security > Full Disk Access) — chat.db is
/// TCC-protected on modern macOS.
final class ChatDatabase {
    private var db: OpaquePointer?

    init(path: String) throws {
        if sqlite3_open_v2(path, &db, SQLITE_OPEN_READONLY, nil) != SQLITE_OK {
            let message = db.map { String(cString: sqlite3_errmsg($0)) } ?? "unknown error"
            sqlite3_close(db)
            throw ChatDatabaseError.openFailed(message)
        }
    }

    deinit {
        sqlite3_close(db)
    }

    /// The highest message ROWID currently in the database. Used so a
    /// freshly-started agent begins "from now" instead of replaying and
    /// replying to years of message history.
    func latestRowID() throws -> Int64 {
        let sql = "SELECT COALESCE(MAX(ROWID), 0) FROM message"
        var statement: OpaquePointer?
        defer { sqlite3_finalize(statement) }
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw ChatDatabaseError.queryFailed(lastError())
        }
        guard sqlite3_step(statement) == SQLITE_ROW else {
            return 0
        }
        return sqlite3_column_int64(statement, 0)
    }

    /// Incoming (is_from_me = 0) messages with ROWID greater than
    /// `sinceRowID`, oldest first.
    func newIncomingMessages(sinceRowID: Int64) throws -> [IncomingMessage] {
        let sql = """
        SELECT m.ROWID, m.guid, m.text, m.date, h.id, c.guid, c.chat_identifier, c.room_name
        FROM message m
        JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
        JOIN chat c ON c.ROWID = cmj.chat_id
        LEFT JOIN handle h ON h.ROWID = m.handle_id
        WHERE m.ROWID > ? AND m.is_from_me = 0
        ORDER BY m.ROWID ASC
        """
        var statement: OpaquePointer?
        defer { sqlite3_finalize(statement) }
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw ChatDatabaseError.queryFailed(lastError())
        }
        sqlite3_bind_int64(statement, 1, sinceRowID)

        var results: [IncomingMessage] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            let rowID = sqlite3_column_int64(statement, 0)
            guard let text = ChatDatabase.text(statement, 2),
                  !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                // Reactions (tapbacks), attachments-only messages, and some
                // rich-text messages on modern macOS carry a NULL `text`
                // column — their content lives instead in the binary
                // `attributedBody` column, which this reader intentionally
                // does not decode. Skip rather than reply to garbage.
                continue
            }
            let guid = ChatDatabase.text(statement, 1) ?? ""
            let dateRaw = sqlite3_column_int64(statement, 3)
            let sender = ChatDatabase.text(statement, 4) ?? ""
            let chatGUID = ChatDatabase.text(statement, 5) ?? ""
            let chatIdentifier = ChatDatabase.text(statement, 6) ?? ""
            let roomName = ChatDatabase.text(statement, 7)

            results.append(IncomingMessage(
                rowID: rowID,
                guid: guid,
                text: text,
                senderHandle: sender,
                chatGUID: chatGUID,
                chatIdentifier: chatIdentifier,
                isGroupChat: roomName != nil,
                date: ChatDatabase.appleDate(fromRaw: dateRaw)
            ))
        }
        return results
    }

    private func lastError() -> String {
        db.map { String(cString: sqlite3_errmsg($0)) } ?? "unknown error"
    }

    private static func text(_ statement: OpaquePointer?, _ index: Int32) -> String? {
        guard let cString = sqlite3_column_text(statement, index) else { return nil }
        return String(cString: cString)
    }

    /// macOS Big Sur+ stores `message.date` as nanoseconds since the Cocoa
    /// reference date (2001-01-01 00:00:00 UTC); older macOS used whole
    /// seconds. Nanosecond values are many orders of magnitude larger, so a
    /// simple threshold disambiguates without an OS version check.
    private static func appleDate(fromRaw raw: Int64) -> Date {
        if raw > 100_000_000_000 {
            return Date(timeIntervalSinceReferenceDate: Double(raw) / 1_000_000_000)
        }
        return Date(timeIntervalSinceReferenceDate: Double(raw))
    }
}
