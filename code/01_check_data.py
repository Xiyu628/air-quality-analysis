"""Check that the required raw data files are present.

This script does not download anything. It prints the official source pages
and verifies that the local files needed by the workflow exist.
"""

from __future__ import annotations

from config import DATA_SOURCES, PROJECT_ROOT


def main() -> None:
    print("Data source checklist\n" + "=" * 24)
    all_ok = True
    for name, info in DATA_SOURCES.items():
        path = info["local_file"]
        exists = path.exists()
        all_ok = all_ok and exists
        status = "OK" if exists else "MISSING"
        print(f"\n{name}")
        print(f"  source: {info['url']}")
        print(f"  local:  {path.relative_to(PROJECT_ROOT)}")
        print(f"  status: {status}")
    if not all_ok:
        raise SystemExit("\nSome required files are missing. See data/README.md.")
    print("\nAll required raw files are available.")


if __name__ == "__main__":
    main()
