# imessage-agent

Native macOS Swift agent that auto-replies to incoming iMessages using
Ollama. No AppleScript CLI shell-out, no third-party bridge server: it reads
`~/Library/Messages/chat.db` directly via the system `libsqlite3`, generates
a reply by calling Ollama's `/api/generate` (the same contract used by
`cpp/src/llm_client.cpp`) over `URLSession`, and sends the reply through
Messages.app using `NSAppleScript`, compiled into this binary.

**Replies send automatically, with no human-approval step.** The only
built-in safety rails are correctness guards, not review gates:
- it never replies to messages it sent itself (`is_from_me`)
- a per-sender cooldown (`OVERLLM_IMESSAGE_COOLDOWN_SECONDS`, default 5s)
  stops it from rapid-fire looping if the other side is also a bot
- group chats are skipped by default (`OVERLLM_IMESSAGE_ALLOW_GROUPS=true`
  to enable — group-chat send via AppleScript `chat id` is less reliable
  across macOS versions than 1:1 buddy sends, so verify manually)

## Requirements

- macOS 13+, Ollama running locally with a model pulled (`ollama pull
  llama3.2`)
- **Full Disk Access** for the compiled binary (or your terminal, if run
  from one): System Settings → Privacy & Security → Full Disk Access.
  `chat.db` is TCC-protected; without this the agent exits on startup.
- **Automation permission for Messages.app**: macOS will prompt for this
  the first time the agent tries to send — approve it, or sends will
  silently fail.

## Build & run

```bash
cd macos/imessage-agent
swift build -c release
.build/release/imessage-agent
```

Or install as a LaunchAgent so it survives logout/reboot:

```bash
swift build -c release
cp .build/release/imessage-agent /usr/local/bin/imessage-agent
cp com.overllm.imessage-agent.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.overllm.imessage-agent.plist
```

## Configuration (environment variables)

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2:latest` | Model to generate replies with |
| `OVERLLM_IMESSAGE_SYSTEM_PROMPT` | see `Config.swift` | System context prepended to every generation |
| `OVERLLM_IMESSAGE_POLL_SECONDS` | `3.0` | chat.db poll interval |
| `OVERLLM_IMESSAGE_ALLOW_GROUPS` | `false` | Auto-reply in group chats |
| `OVERLLM_IMESSAGE_MAX_REPLY_CHARS` | `480` | Hard cap on reply length |
| `OVERLLM_IMESSAGE_COOLDOWN_SECONDS` | `5.0` | Minimum gap between replies to the same sender |
| `OVERLLM_IMESSAGE_STATE_PATH` | `~/.overllm/data/imessage_state.json` | Where last-seen ROWID + cooldown state persists |
| `OVERLLM_IMESSAGE_CHATDB_PATH` | `~/Library/Messages/chat.db` | Override for testing against a copy of chat.db |

## Known limitations

- Messages with no plain-text `text` column (reactions/tapbacks, some
  rich-text messages on modern macOS, which store content in the binary
  `attributedBody` column instead) are skipped rather than decoded.
- Group-chat sends use a best-effort `chat id "<guid>"` AppleScript
  reference; this is known to be flakier across macOS versions than 1:1
  buddy sends. Groups are opt-in for this reason.
- Untested against a live chat.db — this was written in a Linux container
  with no macOS/Swift toolchain available. Build and verify on an actual
  Mac before relying on it.
