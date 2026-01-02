#!/usr/bin/env python3
# [MISE] description="Remove GitHub Actions caches that are for specific PR"
# [USAGE] arg "<pr>" env="PR_NUMBER" help="Caches created for this PR are removed"
import json
import os
import subprocess
from dataclasses import dataclass

# ruff: noqa: T201

LIMIT = 100


@dataclass(kw_only=True, frozen=True)
class CacheEntry:
    id: int
    key: str


def list_caches(pr: int) -> list[CacheEntry]:
    branch = f"refs/pull/{pr}/merge"
    data = json.loads(
        subprocess.run(  # noqa: S603
            [  # noqa: S607
                "gh",
                "cache",
                "list",
                "--ref",
                branch,
                "--limit",
                str(LIMIT),
                "--json",
                "id,key",
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
    )
    return [CacheEntry(**entry) for entry in data]


def remove_cache(entry: CacheEntry) -> None:
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "gh",
            "cache",
            "delete",
            str(entry.id),
        ],
        check=True,
    )


def main() -> None:
    pr = int(os.environ["usage_pr"])  # noqa: SIM112
    print(f"Removing caches for PR {pr}")
    counter = 0
    total_count = 0
    while True:
        caches = list_caches(pr)
        if not caches:
            print(f"Removed {counter} caches for PR {pr}")
            break
        total_count += len(caches)
        total_str = str(total_count)
        if len(caches) == LIMIT:
            total_str += "+"

        for cache in caches:
            counter += 1
            print(f"Removing cache: {counter}/{total_str}: {cache.key}")
            remove_cache(cache)


if __name__ == "__main__":
    main()
