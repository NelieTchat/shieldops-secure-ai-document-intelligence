from metadata import parse_upload_event

good_message = '{"detail": {"bucket": {"name": "shieldops-documents-staging"}, "object": {"key": "quarantine/file1.pdf"}}}'
bad_message = '{"oops": "this is not the right shape"}'

print("--- Testing a valid message ---")
result = parse_upload_event(good_message)
if result:
    print("Bucket:", result.detail.bucket.name)
    print("Key:", result.detail.object.key)

print("--- Testing an invalid message ---")
parse_upload_event(bad_message)
