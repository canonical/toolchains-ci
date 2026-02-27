#!/usr/bin/env python3
"""
Build script for .NET VMR
"""
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd, cwd):
    """Run a shell command and handle errors"""
    print(f"Running: {cmd}", flush=True)
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        check=False
    )
    if result.returncode != 0:
        print(f"Error: Command failed with exit code {result.returncode}", flush=True)
        sys.exit(result.returncode)
    return result


def main():
    """
    Main entry point for building the .NET VMR (Virtual Monolithic Repository).
    Exits with non-zero code if any step fails.
    """
    parser = argparse.ArgumentParser(description="Build .NET VMR")
    parser.add_argument(
        "--repo-root",
        type=str,
        required=True,
        help="Path to the root of the dotnet repository"
    )
    parser.add_argument(
        "--dotnet-version",
        type=int,
        required=True,
        help="Major .NET version being built (e.g., 8, 9, 10)"
    )
    args = parser.parse_args()

    dotnet_path = Path(args.repo_root).resolve()
    dotnet_version = args.dotnet_version

    if not dotnet_path.exists():
        print(f"Error: Path does not exist: {dotnet_path}", flush=True)
        sys.exit(1)

    print(f"Building .NET {dotnet_version} VMR at: {dotnet_path}", flush=True)

    # Determine which prep script to use
    if dotnet_version < 9:
        prep_script = "./prep.sh"
    else:
        prep_script = "./prep-source-build.sh"

    # Run prep script
    print(f"\n=== Running {prep_script} ===", flush=True)
    run_command(prep_script, cwd=dotnet_path)

    # Generate build ID with current date
    build_id = f"{datetime.now().strftime('%Y%m%d')}.1"
    print(f"\n=== Building with ID: {build_id} ===", flush=True)

    # Build command flags based on version
    if dotnet_version == 8:
        build_cmd = "./build.sh --clean-while-building"
    elif dotnet_version == 9:
        build_cmd = """./build.sh \\
        --configuration Release \\
        --verbosity detailed \\
        --source-build \\
        --ci \\
        --clean-while-building"""
    else:
        build_cmd = f"""./build.sh \\
        --configuration Release \\
        --verbosity detailed \\
        --official-build-id {build_id} \\
        --source-build \\
        --ci \\
        --clean-while-building"""

    run_command(build_cmd, cwd=dotnet_path)

    print("\n=== Build completed successfully! ===", flush=True)


if __name__ == "__main__":
    main()
