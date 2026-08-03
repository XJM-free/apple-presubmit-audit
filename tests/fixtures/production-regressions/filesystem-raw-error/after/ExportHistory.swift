import Foundation

@MainActor
final class ExportHistory {
    var emptyState = ""
    var errorMessage = ""

    func load(from directory: URL) {
        guard FileManager.default.fileExists(atPath: directory.path) else {
            emptyState = "No exports yet."
            return
        }
        do {
            _ = try FileManager.default.contentsOfDirectory(
                at: directory,
                includingPropertiesForKeys: nil
            )
        } catch {
            errorMessage = "Exports are unavailable. Try again."
        }
    }
}
