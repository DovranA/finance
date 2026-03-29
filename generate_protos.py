#!/usr/bin/env python3
"""
Generate protobuf Python/gRPC files from proto sources with corrected relative imports.

This script ensures:
1. Consistent --proto_path usage across all proto files
2. Relative imports between generated files in the same package
3. Proper descriptor pool resolution

Usage:
    python generate_protos.py
"""

import subprocess
import sys
import re
from pathlib import Path


def run_protoc(proto_path: str, output_dir: str, proto_files: list[str]) -> None:
    """Run protoc with grpc_tools to generate Python files."""
    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"--proto_path={proto_path}",
        f"--python_out={output_dir}",
        f"--pyi_out={output_dir}",
        f"--grpc_python_out={output_dir}",
        *proto_files,
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=".")

    if result.returncode != 0:
        print(f"ERROR: protoc failed with return code {result.returncode}")
        sys.exit(1)

    print("✓ Protoc generation completed")


def fix_absolute_imports(output_dir: str) -> None:
    """Convert absolute imports to relative imports in generated files."""
    output_path = Path(output_dir)

    # Pattern for absolute imports from event_schemas module
    # Matches: from event_schemas import something_pb2
    absolute_import_pattern = re.compile(
        r"^from event_schemas import (\w+_pb2) as (.+)$", re.MULTILINE
    )

    pb_files = list(output_path.glob("**/*_pb2.py")) + list(
        output_path.glob("**/*_pb2_grpc.py")
    )

    for pb_file in pb_files:
        print(f"Processing {pb_file.name}...")
        content = pb_file.read_text()

        # Replace absolute imports with relative imports
        updated_content = absolute_import_pattern.sub(
            r"from . import \1 as \2", content
        )

        if updated_content != content:
            pb_file.write_text(updated_content)
            print(f"  ✓ Fixed imports in {pb_file.name}")
        else:
            print(f"  - No changes needed in {pb_file.name}")


def main() -> None:
    """Main entry point."""
    # Configuration
    proto_path = "event-schemas"
    output_dir = "app/domain"
    proto_files = [
        "event-schemas/shared.proto",
        "event-schemas/finance.proto",
    ]

    print("=" * 60)
    print("Generating Protocol Buffer Python Files")
    print("=" * 60)
    print(f"Proto path: {proto_path}")
    print(f"Output directory: {output_dir}")
    print(f"Proto files: {', '.join(proto_files)}")
    print()

    # Run protoc
    run_protoc(proto_path, output_dir, proto_files)

    print()
    print("Fixing generated imports...")
    fix_absolute_imports(output_dir)

    print()
    print("=" * 60)
    print("✓ Proto generation completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
