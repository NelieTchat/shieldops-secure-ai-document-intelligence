"""Create users from a Secrets Manager secret (ADR 0014). Runs as a Job, not inside the API.

The secret is a JSON object mapping username to initial password. Existing users are
skipped and never overwritten. Passwords, and anything that could echo one (such as
validation error details), are never logged.
"""
import json
import logging
import os
import sys

import boto3
from pydantic import ValidationError

import config
from auth import security
from db import ensure_tables
from models.schemas import Credentials
from observability import configure_logging
from services import users

log = logging.getLogger("seed_users")


class SeedError(Exception):
    pass


def parse_entries(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise SeedError("The seed secret is not valid JSON.")
    if not isinstance(data, dict) or not data:
        raise SeedError("The seed secret must be a non-empty JSON object of username to password.")
    return data


def read_secret(secret_id: str) -> dict:
    client = boto3.client("secretsmanager", region_name=config.AWS_REGION)
    raw = client.get_secret_value(SecretId=secret_id)["SecretString"]
    return parse_entries(raw)


def seed(entries: dict) -> dict:
    counts = {"created": 0, "skipped": 0, "invalid": 0}
    for position, (username, password) in enumerate(entries.items(), start=1):
        try:
            credentials = Credentials(username=username, password=password)
        except ValidationError:
            counts["invalid"] += 1
            log.error("entry %d rejected: the username or password breaks the policy", position)
            continue
        if users.get_by_username(credentials.username) is not None:
            counts["skipped"] += 1
            log.info("user %s already exists, skipped", credentials.username)
            continue
        try:
            users.create_user(credentials.username, security.hash_password(credentials.password))
        except users.UsernameTaken:
            counts["skipped"] += 1
            log.info("user %s already exists, skipped", credentials.username)
            continue
        counts["created"] += 1
        log.info("user %s created", credentials.username)
    return counts


def main() -> int:
    configure_logging()
    secret_id = os.environ.get("SEED_USERS_SECRET_ID", "")
    if not secret_id:
        log.error("SEED_USERS_SECRET_ID is not set")
        return 2
    config.require_db_config()
    try:
        entries = read_secret(secret_id)
    except SeedError as error:
        log.error("%s", error)
        return 2
    ensure_tables()
    counts = seed(entries)
    log.info("seed finished: created=%d skipped=%d invalid=%d",
             counts["created"], counts["skipped"], counts["invalid"])
    return 1 if counts["invalid"] else 0


if __name__ == "__main__":
    sys.exit(main())
