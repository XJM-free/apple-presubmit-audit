import CloudKit

@MainActor
final class CloudBackupService {
    var errorMessage = ""

    func restore() async {
        do {
            let database = CKContainer.default().privateCloudDatabase
            let recordID = CKRecord.ID(recordName: "backup")
            _ = try await database.record(for: recordID)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
