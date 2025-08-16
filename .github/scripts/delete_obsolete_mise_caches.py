#!/usr/bin/env python3

import contextlib
import json
import os
import subprocess


@contextlib.contextmanager
def log_group(name: str):
    print(f"::group::{name}")
    yield
    print("::endgroup::")


with log_group("Fetching list of cache keys"):
    query_prefix = f"mise-{os.environ['RUNNER_OS']}-"
    result = subprocess.run(
        [
            "gh",
            "cache",
            "list",
            f"--key={query_prefix}",
            "--limit=100",
            "--json=id,key",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    caches = json.loads(result.stdout)

with log_group("Determining which caches to keep"):
    keep_prefix = f"mise-{os.environ['RUNNER_OS']}-{os.environ['MISE_VERSION']}-"
    cacheIdsToDelete = set()
    for item in caches:
        if item["key"].startswith(keep_prefix):
            print(f"Keeping {item['key']} - {item['id']}")
            continue
        print(f"Deleting {item['key']} - {item['id']}")
        cacheIdsToDelete.add(item["id"])

with log_group("Deleting caches..."):
    for cacheId in cacheIdsToDelete:
        print(f"Deleting cache: {cacheId}")
        subprocess.run(["gh", "cache", "delete", str(cacheId)], check=True)
