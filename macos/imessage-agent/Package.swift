// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "imessage-agent",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "imessage-agent",
            path: "Sources/imessage-agent",
            linkerSettings: [
                .linkedLibrary("sqlite3")
            ]
        )
    ]
)
