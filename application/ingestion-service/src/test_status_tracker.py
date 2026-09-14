from status_tracker import ensure_table_exists, record_status

ensure_table_exists()
record_status("shieldops-documents-staging", "quarantine/test-upload.pdf", "received")
print("Status recorded!")
