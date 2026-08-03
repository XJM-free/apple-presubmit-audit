import Foundation

@MainActor
final class ExportHistory {
    var errorMessage = ""

    func load(from directory: URL) {
        do {
            _ = try FileManager.default.contentsOfDirectory(
                at: directory,
                includingPropertiesForKeys: nil
            )
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
