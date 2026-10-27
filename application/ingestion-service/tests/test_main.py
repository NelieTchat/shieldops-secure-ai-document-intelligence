import json

import pytest

import main

KEY = "uploads/user-1/doc-1.txt"
VALID_EVENT = json.dumps({"detail": {"bucket": {"name": "docs-bucket"}, "object": {"key": KEY}}})


class FakeSqs:
    def __init__(self):
        self.sent = []
        self.fail_send = False

    def send_message(self, QueueUrl, MessageBody):
        if self.fail_send:
            raise RuntimeError("send failed")
        self.sent.append((QueueUrl, MessageBody))


@pytest.fixture
def fake_sqs(monkeypatch):
    fake = FakeSqs()
    monkeypatch.setattr(main, "sqs", fake)
    monkeypatch.setattr(main, "PROCESSING_QUEUE_URL", "processing-url")
    monkeypatch.setattr(main, "DLQ_URL", "dlq-url")
    return fake


def test_valid_event_is_recorded_and_forwarded(monkeypatch, fake_sqs):
    recorded = []
    monkeypatch.setattr(main, "record_status", lambda bucket, key, status: recorded.append((bucket, key, status)))
    assert main.process_message(VALID_EVENT) is True
    assert recorded == [("docs-bucket", KEY, "received")]
    assert fake_sqs.sent == [("processing-url", json.dumps({"bucket": "docs-bucket", "key": KEY}))]


def test_invalid_event_is_copied_to_the_dlq_and_acknowledged(monkeypatch, fake_sqs):
    monkeypatch.setattr(main, "record_status", lambda *args: pytest.fail("must not record an invalid event"))
    assert main.process_message("not json at all") is True
    assert fake_sqs.sent == [("dlq-url", "not json at all")]


def test_invalid_event_without_a_dlq_is_dropped_but_acknowledged(monkeypatch, fake_sqs):
    monkeypatch.setattr(main, "DLQ_URL", "")
    assert main.process_message("not json at all") is True
    assert fake_sqs.sent == []


def test_dlq_failure_leaves_the_message_for_retry(fake_sqs):
    fake_sqs.fail_send = True
    assert main.process_message("not json at all") is False


def test_status_failure_leaves_the_message_for_retry(monkeypatch, fake_sqs):
    def db_down(*args):
        raise RuntimeError("db down")

    monkeypatch.setattr(main, "record_status", db_down)
    assert main.process_message(VALID_EVENT) is False
    assert fake_sqs.sent == []


def test_forward_failure_leaves_the_message_for_retry(monkeypatch, fake_sqs):
    monkeypatch.setattr(main, "record_status", lambda *args: None)
    fake_sqs.fail_send = True
    assert main.process_message(VALID_EVENT) is False
