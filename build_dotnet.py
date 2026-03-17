#!/usr/bin/env python3
"""
Build script for .NET VMR
"""
import argparse
import glob
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DOTNET_DEVEL_VERSION = 11  # Update this as needed for future versions

def run_command(cmd: str, cwd: Path | None) -> subprocess.CompletedProcess[bytes]:
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


def get_current_ubuntu_version() -> str:
    """Get the current Ubuntu version as a string (e.g., 20.04 -> 20.04)"""
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VERSION_ID="):
                    version_str = line.split("=")[1].strip().strip('"')
                    return version_str
    except Exception as e:
        print(f"Error reading Ubuntu version: {e}", flush=True)
        sys.exit(1)
    print("Could not determine Ubuntu version", flush=True)
    sys.exit(1)


def install_previous_dotnet(dotnet_version: int, dotnet_vmr_root: Path):
    """Install the previous version of .NET if needed"""
    if dotnet_version < DOTNET_DEVEL_VERSION:
        current_ubuntu_version = get_current_ubuntu_version()
        if current_ubuntu_version in ["22.04", "24.04", "26.04"]:
            # Add backports PPA for older versions of .NET on newer Ubuntu releases
            print(f"Adding backports PPA for .NET {dotnet_version} on Ubuntu {current_ubuntu_version}...", flush=True)
            run_command("add-apt-repository -y ppa:dotnet/backports", cwd=Path.home())

        print("Installing .NET SDK for source-build...", flush=True)
        install_cmd = f"""apt-get update && apt-get install -y dotnet-sdk-{dotnet_version}.0 \\
                dotnet-sdk-{dotnet_version}.0-source-built-artifacts"""
        run_command(install_cmd, cwd=Path.home())
    else:
        prep_script = "./prep-source-build.sh --no-binary-removal"
        # Run prep script
        print(f"\n=== Running {prep_script} ===", flush=True)
        run_command(prep_script, cwd=dotnet_vmr_root)


def prepare_previously_source_built_artifacts(dotnet_version: int, dotnet_vmr_root: Path):
    """Prepare previously source-built artifacts for the build"""
    if dotnet_version < DOTNET_DEVEL_VERSION:
        dotnet_prereqs_packages_dir = Path(f"{dotnet_vmr_root}/prereqs/packages/archive").resolve()
        if not dotnet_prereqs_packages_dir.exists():
            print(f"Error: Prerequisites packages directory does not exist: {dotnet_prereqs_packages_dir}", flush=True)
            sys.exit(1)

        dotnet_root_dir = Path("/usr/lib/dotnet").resolve()
        pattern = os.path.join(
            dotnet_root_dir,
            "source-built-artifacts",
            f"Private.SourceBuilt.Artifacts.{dotnet_version}.0.*.tar.gz",
        )
        artifacts_tarball = glob.glob(pattern)
        if not artifacts_tarball:
            print(f"Error: No source-built artifacts found for .NET {dotnet_version} at {pattern}", flush=True)
            sys.exit(1)
        if len(artifacts_tarball) > 1:
            print(f"Error: Multiple source-built artifacts found for .NET {dotnet_version} at {pattern}", flush=True)
            sys.exit(1)
        print(f"Copying source-built artifacts from {artifacts_tarball[0]}...", flush=True)

        # Link prereqs tarball to the expected location in the VMR
        run_command(f"ln --symbolic {artifacts_tarball[0]} {dotnet_prereqs_packages_dir}", cwd=dotnet_vmr_root)

        # Copy .NET SDK to the VMR
        run_command(f"""cp --recursive --dereference --preserve=mode,ownership,timestamps \\
                    {dotnet_root_dir} {dotnet_vmr_root}/previously-built-dotnet""", cwd=dotnet_vmr_root)


def build_cmd(dotnet_vmr_root: Path, dotnet_version: int, build_id: str) -> str:
    """Construct the build command for the .NET VMR"""
    # Start with .NET 8 baseline
    cmd = [
        "./build.sh",
        "--clean-while-building"]

    # For .NET 9 and above, add more parameters
    if dotnet_version >= 9:
        cmd.append("--ci")
        cmd.append("--source-only")
        cmd.append("--verbosity normal")
        cmd.append("--configuration Release")

    # For .NET 10 and above, add official build id
    if dotnet_version >= 10:
        cmd.append(f"--official-build-id {build_id}")

    # If not devel, use previously built .NET SDK
    if dotnet_version < DOTNET_DEVEL_VERSION:
        cmd.append(f"--with-sdk {dotnet_vmr_root}/previously-built-dotnet")

    # Additional MSBuild parameters:
    msbuild_params = [
        "/p:SkipPortableRuntimeBuild=true",
        "/p:ContinueOnPrebuiltBaselineError=true",
        # Binary scan is failing on the CI with "An error occurred trying to start process
        # 'file' with working directory '/__w/dotnet-ci/dotnet-ci/dotnet-vmr/eng'.
        # No such file or directory" error, so we will skip it for now.
        "/p:SkipBinaryScan=true",
        # Skipping binary publishing because of error: Could not copy the file
        # "/__w/dotnet-ci/dotnet-ci/dotnet-vmr/artifacts/log/Release/binary-report/NewBinaries.txt"
        # because it was not found.
        "/p:SkipDetectBinaries=true",
    ]

    if len(msbuild_params) > 0:
        cmd.append("--")
        cmd.extend(msbuild_params)

    # Join with line continuation for readability
    return " \\\n    ".join(cmd)


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

    dotnet_vmr_root = Path(args.repo_root).resolve()
    dotnet_version = args.dotnet_version

    if not dotnet_vmr_root.exists():
        print(f"Error: Path does not exist: {dotnet_vmr_root}", flush=True)
        sys.exit(1)

    install_previous_dotnet(dotnet_version, dotnet_vmr_root)

    prepare_previously_source_built_artifacts(dotnet_version, dotnet_vmr_root)

    # ===================================================================
    # Create a global MSBuild override file to prevent compiler deadlocks
    # ===================================================================
    override_file = Path("/tmp/disable-nodes.targets")
    with open(override_file, "w", encoding="utf-8") as f:
        f.write("""<Project>
  <PropertyGroup>
    <UseSharedCompilation>false</UseSharedCompilation>
    <UseRazorBuildServer>false</UseRazorBuildServer>
  </PropertyGroup>
</Project>""")

    # Instruct ALL nested MSBuild processes to implicitly import this file
    os.environ["CustomAfterMicrosoftCommonTargets"] = str(override_file)
    os.environ["CustomAfterMicrosoftCommonCrossTargetingTargets"] = str(override_file)
    # ===================================================================

    print(f"Building .NET {dotnet_version} VMR at: {dotnet_vmr_root}", flush=True)

    # Generate build ID with current date
    build_id = f"{datetime.now().strftime('%Y%m%d')}.1"
    print(f"\n=== Building with ID: {build_id} ===", flush=True)

    run_command(build_cmd(dotnet_vmr_root, dotnet_version, build_id), cwd=dotnet_vmr_root)

    print("\n=== Build completed successfully! ===", flush=True)


if __name__ == "__main__":
    main()
