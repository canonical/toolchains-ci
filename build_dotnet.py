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
    args = parser.parse_args()

    dotnet_path = Path(args.repo_root).resolve()

    if not dotnet_path.exists():
        print(f"Error: Path does not exist: {dotnet_path}", flush=True)
        sys.exit(1)

    print(f"Building .NET VMR at: {dotnet_path}", flush=True)

    # Run prep script
    print("\n=== Running prep-source-build.sh ===", flush=True)
    run_command("./prep-source-build.sh", cwd=dotnet_path)

    # Generate build ID with current date
    build_id = f"{datetime.now().strftime('%Y%m%d')}.1"
    print(f"\n=== Building with ID: {build_id} ===", flush=True)

    # Run build script
    build_cmd = f"""./build.sh \\
        --configuration Release \\
        --verbosity diagnostic \\
        --official-build-id {build_id} \\
        --source-build \\
        --ci \\
        --clean-while-building"""

    run_command(build_cmd, cwd=dotnet_path)

    print("\n=== Build completed successfully! ===", flush=True)


if __name__ == "__main__":
    main()
