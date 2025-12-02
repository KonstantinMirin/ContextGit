#!/usr/bin/env python3
"""Comprehensive system verification for contextgit MVP.

This script performs a complete validation of the contextgit implementation:
1. Import validation
2. CLI command registration
3. Python syntax verification
4. Module structure verification
5. Documentation completeness check
"""

import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_result(test_name, passed, message=""):
    """Print test result."""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status:8} {test_name}")
    if message:
        print(f"         {message}")


def verify_imports():
    """Verify all imports work."""
    print_header("1. Import Validation")

    try:
        # Run import test script
        result = subprocess.run(
            [sys.executable, "test_imports.py"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        passed = result.returncode == 0
        print_result("All imports validate", passed)

        if not passed:
            print("\nImport errors:")
            print(result.stderr)

        return passed
    except Exception as e:
        print_result("Import validation", False, str(e))
        return False


def verify_cli_commands():
    """Verify all CLI commands are registered."""
    print_header("2. CLI Command Registration")

    expected_commands = [
        "init", "scan", "status", "show", "extract",
        "link", "confirm", "next-id", "relevant-for-file", "fmt"
    ]

    try:
        result = subprocess.run(
            [sys.executable, "-m", "contextgit", "--help"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print_result("CLI help command", False)
            return False

        output = result.stdout
        all_present = all(cmd in output for cmd in expected_commands)

        print_result("All 10 commands registered", all_present)

        if all_present:
            print(f"         Commands: {', '.join(expected_commands)}")
        else:
            missing = [cmd for cmd in expected_commands if cmd not in output]
            print(f"         Missing: {', '.join(missing)}")

        return all_present
    except Exception as e:
        print_result("CLI command check", False, str(e))
        return False


def verify_command_help():
    """Verify each command has help text."""
    print_header("3. Individual Command Help")

    commands = [
        "init", "scan", "status", "show", "extract",
        "link", "confirm", "next-id", "relevant-for-file", "fmt"
    ]

    all_passed = True
    for cmd in commands:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "contextgit", cmd, "--help"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=5
            )

            passed = result.returncode == 0 and len(result.stdout) > 100
            print_result(f"{cmd} --help", passed)

            if not passed:
                all_passed = False
        except Exception as e:
            print_result(f"{cmd} --help", False, str(e))
            all_passed = False

    return all_passed


def verify_python_syntax():
    """Verify all Python files compile without errors."""
    print_header("4. Python Syntax Verification")

    py_files = list((project_root / "contextgit").rglob("*.py"))

    errors = []
    for py_file in py_files:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                errors.append((py_file.name, result.stderr))
        except Exception as e:
            errors.append((py_file.name, str(e)))

    passed = len(errors) == 0
    print_result(f"All {len(py_files)} Python files compile", passed)

    if not passed:
        print("\nSyntax errors:")
        for filename, error in errors:
            print(f"  {filename}: {error}")

    return passed


def verify_module_structure():
    """Verify expected module structure exists."""
    print_header("5. Module Structure Verification")

    expected_modules = {
        "CLI layer": [
            "contextgit/cli/app.py",
            "contextgit/cli/commands.py",
        ],
        "Handlers": [
            "contextgit/handlers/init_handler.py",
            "contextgit/handlers/scan_handler.py",
            "contextgit/handlers/status_handler.py",
            "contextgit/handlers/show_handler.py",
            "contextgit/handlers/extract_handler.py",
            "contextgit/handlers/link_handler.py",
            "contextgit/handlers/confirm_handler.py",
            "contextgit/handlers/next_id_handler.py",
            "contextgit/handlers/relevant_handler.py",
            "contextgit/handlers/fmt_handler.py",
        ],
        "Domain": [
            "contextgit/domain/checksum/calculator.py",
            "contextgit/domain/config/manager.py",
            "contextgit/domain/id_gen/generator.py",
            "contextgit/domain/index/manager.py",
            "contextgit/domain/linking/engine.py",
            "contextgit/domain/location/resolver.py",
            "contextgit/domain/location/snippet.py",
            "contextgit/domain/metadata/parser.py",
        ],
        "Infrastructure": [
            "contextgit/infra/filesystem.py",
            "contextgit/infra/yaml_io.py",
            "contextgit/infra/output.py",
        ],
        "Models": [
            "contextgit/models/node.py",
            "contextgit/models/link.py",
            "contextgit/models/index.py",
            "contextgit/models/config.py",
            "contextgit/models/location.py",
            "contextgit/models/enums.py",
        ],
    }

    all_passed = True
    for layer, modules in expected_modules.items():
        missing = []
        for module in modules:
            module_path = project_root / module
            if not module_path.exists():
                missing.append(module)

        passed = len(missing) == 0
        print_result(f"{layer} ({len(modules)} modules)", passed)

        if not passed:
            print(f"         Missing: {', '.join(missing)}")
            all_passed = False

    return all_passed


def verify_documentation():
    """Verify documentation completeness."""
    print_header("6. Documentation Verification")

    required_docs = {
        "README.md": "User-facing documentation",
        "CLAUDE.md": "Claude Code instructions",
        "IMPLEMENTATION_COMPLETE.md": "Implementation summary",
        "docs/01_product_overview.md": "Product overview",
        "docs/04_architecture_overview.md": "Architecture design",
        "docs/06_cli_specification.md": "CLI specification",
    }

    all_passed = True
    for doc_path, description in required_docs.items():
        doc_file = project_root / doc_path
        passed = doc_file.exists()
        print_result(f"{doc_path}", passed, description if passed else "Missing")

        if not passed:
            all_passed = False

    return all_passed


def verify_entry_points():
    """Verify package entry points work."""
    print_header("7. Entry Point Verification")

    tests = [
        ("python -m contextgit", [sys.executable, "-m", "contextgit", "--help"]),
        ("Direct module import", [sys.executable, "-c", "import contextgit; print('OK')"]),
    ]

    all_passed = True
    for name, cmd in tests:
        try:
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=5
            )

            passed = result.returncode == 0
            print_result(name, passed)

            if not passed:
                all_passed = False
        except Exception as e:
            print_result(name, False, str(e))
            all_passed = False

    return all_passed


def main():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("  CONTEXTGIT MVP SYSTEM VERIFICATION")
    print("=" * 70)

    results = {
        "Import Validation": verify_imports(),
        "CLI Command Registration": verify_cli_commands(),
        "Command Help Text": verify_command_help(),
        "Python Syntax": verify_python_syntax(),
        "Module Structure": verify_module_structure(),
        "Documentation": verify_documentation(),
        "Entry Points": verify_entry_points(),
    }

    # Summary
    print_header("VERIFICATION SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓" if result else "✗"
        print(f"  {status} {test_name}")

    print("\n" + "=" * 70)

    if passed == total:
        print(f"  SUCCESS: All {total} verification tests passed!")
        print("  contextgit MVP is ready for integration testing.")
    else:
        failed = total - passed
        print(f"  PARTIAL: {passed}/{total} tests passed ({failed} failed)")
        print("  Please review failures above.")

    print("=" * 70 + "\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
