#!/usr/bin/env python3

import contextlib
import json
import os
import subprocess
from collections.abc import Iterator


@contextlib.contextmanager
def log_group(name: str) -> Iterator[None]:
    print(f"::group::{name}")
    yield
    print("::endgroup::")


def main() -> None:
    with log_group("Fetching list of cache keys"):
        query_prefix = "mise-"
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "gh",
                "cache",
                "list",
                "--ref=main",
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
        keep_prefix = f"{query_prefix}{os.environ['MISE_VERSION']}-"
        cache_ids_to_delete = set()
        for item in caches:
            if item["key"].startswith(keep_prefix):
                print(f"Keeping {item['key']} - {item['id']}")
                continue
            print(f"Deleting {item['key']} - {item['id']}")
            cache_ids_to_delete.add(item["id"])

    with log_group("Deleting caches..."):
        for cache_id in cache_ids_to_delete:
            print(f"Deleting cache: {cache_id}")
            subprocess.run(["gh", "cache", "delete", str(cache_id)], check=True)  # noqa: S603, S607


if __name__ == "__main__":
    main()
