from metadata import parse_upload_event

GOOD = (
    '{"detail": {"bucket": {"name": "shieldops-documents-staging"}, '
    '"object": {"key": "quarantine/file1.pdf"}}}'
)


def test_valid_upload_event_is_parsed():
    result = parse_upload_event(GOOD)
    assert result.detail.bucket.name == "shieldops-documents-staging"
    assert result.detail.object.key == "quarantine/file1.pdf"


def test_wrong_shape_is_rejected():
    assert not parse_upload_event('{"oops": "this is not the right shape"}')


def test_malformed_json_is_rejected():
    assert not parse_upload_event("not json at all")
