import CloudKit

struct SyncService {
    let container = CKContainer(identifier: "iCloud.com.example.fixture")

    func syncSnapshot() async throws {
        let database = container.privateCloudDatabase
        let recordID = CKRecord.ID(recordName: "root")
        let record: CKRecord
        if let existing = try? await database.record(for: recordID) {
            record = existing
        } else {
            record = CKRecord(recordType: "Document", recordID: recordID)
        }
        try await database.save(record)
    }
}
