import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from packaging.specifiers import SpecifierSet
from packaging.version import Version


def check_requirements(file_path):
    lines = [
        line.strip()
        for line in Path(file_path).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    total_checked = len(lines)
    not_found = 0
    incompatible_311 = 0

    highest_min_version = None
    highest_requirement_str = "None"

    for line in lines:
        if "==" in line:
            name, version = [part.strip() for part in line.split("==", 1)]
            url = f"https://pypi.org/pypi/{name}/{version}/json"
        else:
            name = line.strip()
            version = ""
            url = f"https://pypi.org/pypi/{name}/json"

        req = urllib.request.Request(
            url, headers={"User-Agent": "ase-entry-test/1.0"}
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                not_found += 1
                continue
            raise

        info = data.get("info", {})
        if not version:
            version = info.get("version", "")

        req_python = info.get("requires_python")

        # A release without requires_python counts as compatible
        if req_python:
            spec_set = SpecifierSet(req_python)

            # Check compatibility with Python 3.11 (handles lower and upper bounds)
            if "3.11" not in spec_set:
                incompatible_311 += 1

            # Check minimum required Python version
            pkg_min_ver = None
            pkg_min_spec = None
            for spec in spec_set:
                if spec.operator in (">=", ">", "~=", "=="):
                    clean_ver = spec.version.replace(".*", "")
                    v = Version(clean_ver)
                    if pkg_min_ver is None or v > pkg_min_ver:
                        pkg_min_ver = v
                        pkg_min_spec = spec

            if pkg_min_ver is not None:
                if (
                    highest_min_version is None
                    or pkg_min_ver > highest_min_version
                ):
                    highest_min_version = pkg_min_ver
                    highest_requirement_str = (
                        f"{name.lower()}=={version} ({pkg_min_spec})"
                    )

    print(f"Dependencies checked: {total_checked}")
    print(f"Not found on PyPI: {not_found}")
    print(f"Incompatible with Python 3.11: {incompatible_311}")
    print(f"Highest requirement: {highest_requirement_str}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    elif Path("requirements.txt").exists():
        target_file = "requirements.txt"
    else:
        target_file = "requirement.txt"

    check_requirements(target_file)
