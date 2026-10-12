import CloudKit

@MainActor
final class CloudBackupService {
    var emptyState = ""
    var errorMessage = ""

    func restore() async {
        do {
            let database = CKContainer.default().privateCloudDatabase
            let recordID = CKRecord.ID(recordName: "backup")
            _ = try await database.record(for: recordID)
        } catch let cloudError as CKError where cloudError.code == .unknownItem {
            emptyState = "No cloud backup yet."
        } catch {
            errorMessage = stableMessage(for: error)
        }
    }

    private func stableMessage(for error: Error) -> String {
        "Cloud backup is unavailable. Try again."
    }
}
