import Foundation

/// Polls chat.db for new incoming iMessages, generates a reply via Ollama,
/// and sends it back immediately through Messages.app — fully autonomous,
/// no approval step. Loop-prevention (never reply to own messages, a
/// per-sender cooldown, and group chats disabled by default) is a
/// correctness requirement, not an approval gate.
@main
struct ImessageOllamaAgent {
    static func main() async {
        let config = Config.fromEnvironment()
        print("[imessage-agent] starting — model=\(config.ollamaModel) poll=\(config.pollIntervalSeconds)s groups=\(config.allowGroupChats)")

        let ollama = OllamaClient(host: config.ollamaHost, model: config.ollamaModel)
        let sender = MessageSender()
        var state = ReplyState.load(path: config.stateFilePath)

        let db: ChatDatabase
        do {
            db = try ChatDatabase(path: config.chatDBPath)
        } catch {
            fputs("[imessage-agent] fatal: \(error)\n", stderr)
            fputs("[imessage-agent] this process needs Full Disk Access to read chat.db: System Settings > Privacy & Security > Full Disk Access\n", stderr)
            exit(1)
        }

        if state.lastProcessedRowID == 0 {
            // First run: start "from now" so the agent never replies to
            // years of prior message history on its very first launch.
            state.lastProcessedRowID = (try? db.latestRowID()) ?? 0
            state.save(path: config.stateFilePath)
            print("[imessage-agent] first run — starting from ROWID \(state.lastProcessedRowID)")
        }

        while true {
            await pollOnce(config: config, db: db, ollama: ollama, sender: sender, state: &state)
            try? await Task.sleep(nanoseconds: UInt64(config.pollIntervalSeconds * 1_000_000_000))
        }
    }

    private static func pollOnce(config: Config, db: ChatDatabase, ollama: OllamaClient, sender: MessageSender, state: inout ReplyState) async {
        let messages: [IncomingMessage]
        do {
            messages = try db.newIncomingMessages(sinceRowID: state.lastProcessedRowID)
        } catch {
            fputs("[imessage-agent] poll error: \(error)\n", stderr)
            return
        }

        for message in messages {
            state.lastProcessedRowID = max(state.lastProcessedRowID, message.rowID)

            if message.isGroupChat && !config.allowGroupChats {
                print("[imessage-agent] skip group message from \(message.senderHandle) (groups disabled, set OVERLLM_IMESSAGE_ALLOW_GROUPS=true to enable)")
                continue
            }

            if let lastReply = state.lastReplyBySender[message.senderHandle],
               Date().timeIntervalSince(lastReply) < config.cooldownSeconds {
                print("[imessage-agent] skip \(message.senderHandle): cooldown active")
                continue
            }

            print("[imessage-agent] <- \(message.senderHandle): \(message.text)")

            do {
                var reply = try await ollama.generate(prompt: message.text, systemContext: config.systemPrompt)
                if reply.isEmpty {
                    print("[imessage-agent] empty reply from Ollama, skipping send")
                    continue
                }
                if reply.count > config.maxReplyChars {
                    reply = String(reply.prefix(config.maxReplyChars))
                }

                if message.isGroupChat {
                    try sender.sendToChat(chatGUID: message.chatGUID, text: reply)
                } else {
                    try sender.sendToBuddy(handle: message.senderHandle, text: reply)
                }

                state.lastReplyBySender[message.senderHandle] = Date()
                print("[imessage-agent] -> \(message.senderHandle): \(reply)")
            } catch {
                fputs("[imessage-agent] reply failed for \(message.senderHandle): \(error)\n", stderr)
            }
        }

        state.save(path: config.stateFilePath)
    }
}
