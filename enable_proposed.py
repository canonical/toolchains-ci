#!/usr/bin/env python3
"""
Enable the -proposed pocket for Ubuntu package repositories.

This script configures APT to use the -proposed pocket, supporting both
the traditional sources.list format (Ubuntu < 24.04) and the modern
DEB822 format (Ubuntu 24.04+).
"""

import os
import sys
from pathlib import Path


def get_ubuntu_codename():
    """Extract the Ubuntu codename from /etc/os-release."""
    try:
        with open('/etc/os-release', 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('VERSION_CODENAME='):
                    return line.strip().split('=')[1]
    except FileNotFoundError:
        print("Error: /etc/os-release not found", file=sys.stderr)
        sys.exit(1)

    print("Error: VERSION_CODENAME not found in /etc/os-release", file=sys.stderr)
    sys.exit(1)


def uses_deb822_format():
    """Check if the system uses DEB822 format (Ubuntu 24.04+)."""
    sources_list_d = Path('/etc/apt/sources.list.d')
    ubuntu_sources = sources_list_d / 'ubuntu.sources'
    return sources_list_d.is_dir() and ubuntu_sources.is_file()


def enable_proposed_deb822(codename: str):
    """Enable -proposed pocket using DEB822 format."""
    print("Using DEB822 format (Ubuntu 24.04+)")

    # Add proposed pocket to ubuntu.sources
    sources_content = f"""Types: deb
URIs: http://archive.ubuntu.com/ubuntu/
Suites: {codename}-proposed
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
"""

    with open('/etc/apt/sources.list.d/ubuntu.sources', 'a', encoding='utf-8') as f:
        f.write(sources_content)

    # Create preferences file for dotnet packages
    preferences_content = f"""Package: src:dotnet*
Pin: release a={codename}-proposed
Pin-Priority: 990
"""

    with open('/etc/apt/preferences.d/dotnet-proposed', 'w', encoding='utf-8') as f:
        f.write(preferences_content)


def enable_proposed_traditional(codename: str):
    """Enable -proposed pocket using traditional sources.list format."""
    print("Using traditional sources.list format (Ubuntu < 24.04)")

    # Add proposed pocket to sources.list
    proposed_line = f"deb http://archive.ubuntu.com/ubuntu/ {codename}-proposed main restricted universe multiverse\n"

    with open('/etc/apt/sources.list', 'a', encoding='utf-8') as f:
        f.write(proposed_line)


def main():
    """Main entry point."""
    # Check if running as root
    if os.geteuid() != 0:
        print("Error: This script must be run as root", file=sys.stderr)
        sys.exit(1)

    codename = get_ubuntu_codename()

    if uses_deb822_format():
        enable_proposed_deb822(codename)
    else:
        enable_proposed_traditional(codename)

    print(f"Proposed pocket enabled for {codename}")


if __name__ == '__main__':
    main()
