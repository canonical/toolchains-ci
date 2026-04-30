#!/usr/bin/env python3
"""Extract the .NET SDK or Runtime version from a dotnet-source repository."""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree


def get_branch(repo_root: Path) -> str:
    """Return the currently checked-out branch name of the given git repository."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_major_version(branch: str) -> int | None:
    """Return the major version from branch name, or None for main/devel branches."""
    match = re.match(r"^release/(\d+)\.\d+\.\d+xx$", branch)
    if match:
        return int(match.group(1))
    return None


def read_xml_property(props_file: Path, *property_names: str) -> dict[str, str]:
    """Parse an MSBuild props file and return the requested property values."""
    tree = ElementTree.parse(props_file)
    root = tree.getroot()
    values: dict[str, str] = {}
    for elem in root.iter():
        local_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local_tag in property_names and elem.text:
            values[local_tag] = elem.text.strip()
    return values


def get_sdk_version(repo_root: Path, major_version: int | None, include_prerelease: bool = True) -> str:
    """Read and return the .NET SDK version string from the repository."""
    props_file = repo_root / "src" / "sdk" / "eng" / "Versions.props"
    if not props_file.exists():
        print(f"error: {props_file} not found", file=sys.stderr)
        sys.exit(1)

    if major_version == 8:
        props = read_xml_property(props_file, "VersionPrefix")
        if "VersionPrefix" not in props:
            print("error: VersionPrefix not found in Versions.props", file=sys.stderr)
            sys.exit(1)
        return props["VersionPrefix"]

    props = read_xml_property(
        props_file,
        "VersionMajor",
        "VersionMinor",
        "VersionSDKMinor",
        "VersionSDKMinorPatch",
        "VersionFeature",
        "PreReleaseVersionLabel",
        "PreReleaseVersionIteration",
    )
    for key in ("VersionMajor", "VersionMinor", "VersionSDKMinor"):
        if key not in props:
            print(f"error: {key} not found in Versions.props", file=sys.stderr)
            sys.exit(1)
    if "VersionSDKMinorPatch" in props:
        patch = props["VersionSDKMinorPatch"].zfill(2)
    elif "VersionFeature" in props:
        patch = props["VersionFeature"].zfill(2)
    else:
        print("error: neither VersionSDKMinorPatch nor VersionFeature found in Versions.props", file=sys.stderr)
        sys.exit(1)
    version = (
        f"{props['VersionMajor']}.{props['VersionMinor']}."
        f"{props['VersionSDKMinor']}{patch}"
    )
    if major_version is None and include_prerelease:
        for key in ("PreReleaseVersionLabel", "PreReleaseVersionIteration"):
            if key not in props:
                print(f"error: {key} not found in Versions.props", file=sys.stderr)
                sys.exit(1)
        version += f"-{props['PreReleaseVersionLabel']}.{props['PreReleaseVersionIteration']}"
    return version


def get_runtime_version(repo_root: Path, major_version: int | None, include_prerelease: bool = True) -> str:
    """Read and return the .NET Runtime version string from the repository."""
    props_file = repo_root / "src" / "runtime" / "eng" / "Versions.props"
    if not props_file.exists():
        print(f"error: {props_file} not found", file=sys.stderr)
        sys.exit(1)

    props = read_xml_property(
        props_file,
        "MajorVersion",
        "MinorVersion",
        "PatchVersion",
        "PreReleaseVersionLabel",
        "PreReleaseVersionIteration",
    )
    for key in ("MajorVersion", "MinorVersion", "PatchVersion"):
        if key not in props:
            print(f"error: {key} not found in Versions.props", file=sys.stderr)
            sys.exit(1)
    version = f"{props['MajorVersion']}.{props['MinorVersion']}.{props['PatchVersion']}"
    if major_version is None and include_prerelease:
        for key in ("PreReleaseVersionLabel", "PreReleaseVersionIteration"):
            if key not in props:
                print(f"error: {key} not found in Versions.props", file=sys.stderr)
                sys.exit(1)
        version += f"-{props['PreReleaseVersionLabel']}.{props['PreReleaseVersionIteration']}"
    return version


def get_ubuntu_source_package(repo_root: Path, major_version: int | None) -> str:
    """Return the Ubuntu source package version string for the .NET repository."""
    sdk = get_sdk_version(repo_root, major_version, include_prerelease=False)
    runtime = get_runtime_version(repo_root, major_version, include_prerelease=False)
    if major_version is None:
        # Read pre-release info from the runtime props.
        props_file = repo_root / "src" / "runtime" / "eng" / "Versions.props"
        props = read_xml_property(props_file, "PreReleaseVersionLabel", "PreReleaseVersionIteration")
        for key in ("PreReleaseVersionLabel", "PreReleaseVersionIteration"):
            if key not in props:
                print(f"error: {key} not found in runtime Versions.props", file=sys.stderr)
                sys.exit(1)
        return f"{sdk}-{runtime}~{props['PreReleaseVersionLabel']}{props['PreReleaseVersionIteration']}"
    return f"{sdk}-{runtime}-0ubuntu1"


def main() -> None:
    """Parse arguments and print the requested .NET version."""
    parser = argparse.ArgumentParser(
        description="Extract .NET SDK or Runtime version from a source repository."
    )
    parser.add_argument(
        "--repo-root",
        required=True,
        help="Path to the root of the .NET source repository",
    )
    parser.add_argument(
        "--product",
        required=True,
        choices=["sdk", "runtime", "ubuntu-source-package"],
        help="Which version to output: 'sdk', 'runtime', or 'ubuntu-source-package'",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.is_dir():
        print(f"error: {repo_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    branch = get_branch(repo_root)
    major_version = get_major_version(branch)

    if args.product == "sdk":
        print(get_sdk_version(repo_root, major_version))
    elif args.product == "runtime":
        print(get_runtime_version(repo_root, major_version))
    else:
        print(get_ubuntu_source_package(repo_root, major_version))


if __name__ == "__main__":
    main()
