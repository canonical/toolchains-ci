# Ubuntu Toolchains CI

This repository contains continuous integration scripts for performing daily builds of various toolchains available in Ubuntu. The purpose is to ensure toolchain quality and identify issues early in the development cycle.

## Overview

The repository is organized by toolchain, with each toolchain having its own directory containing build scripts and configuration files. Daily CI runs build and test these toolchains to validate their functionality on Ubuntu.

## Supported Toolchains

Currently supported toolchains:
- **.NET** - Microsoft's .NET SDK and runtime

Additional toolchains will be added over time.

## Repository Structure

```
.
├── dotnet/          # .NET toolchain build scripts
├── eng/             # Engineering tools and utilities
└── README.md        # This file
```

## Usage

Each toolchain directory contains its own build script that can be executed independently. The scripts are designed to be run in a CI environment with appropriate Ubuntu configurations.

## Contributing

When adding a new toolchain:
1. Create a new directory for the toolchain
2. Add build and test scripts following the existing patterns
3. Create your workflow file in the `.github/workflows/` directory to automate the CI process for the new toolchain
4. Update this README with the new toolchain information
