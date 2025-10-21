"""
Test script to verify the pipeline setup and configuration.

This script checks that all dependencies are installed correctly and the
basic infrastructure is working.

Usage:
    python scripts/test_setup.py
"""

import sys
from pathlib import Path

# Note: Since the package is installed with 'pip install -e .',
# we can import directly without path manipulation


def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")

    try:
        import requests
        print("  ✓ requests")
    except ImportError as e:
        print(f"  ✗ requests: {e}")
        return False

    try:
        from pyrate_limiter import Duration, Limiter, Rate
        print("  ✓ pyrate_limiter")
    except ImportError as e:
        print(f"  ✗ pyrate_limiter: {e}")
        return False

    try:
        from tenacity import retry
        print("  ✓ tenacity")
    except ImportError as e:
        print(f"  ✗ tenacity: {e}")
        return False

    try:
        import pandas
        print("  ✓ pandas")
    except ImportError as e:
        print(f"  ✗ pandas: {e}")
        return False

    try:
        import numpy
        print("  ✓ numpy")
    except ImportError as e:
        print(f"  ✗ numpy: {e}")
        return False

    try:
        from pydantic import BaseModel
        print("  ✓ pydantic")
    except ImportError as e:
        print(f"  ✗ pydantic: {e}")
        return False

    try:
        from dotenv import load_dotenv
        print("  ✓ python-dotenv")
    except ImportError as e:
        print(f"  ✗ python-dotenv: {e}")
        return False

    try:
        import yaml
        print("  ✓ pyyaml")
    except ImportError as e:
        print(f"  ✗ pyyaml: {e}")
        return False

    return True


def test_internal_modules():
    """Test that internal modules can be imported."""
    print("\nTesting internal modules...")

    try:
        from utils.logger import setup_logging
        print("  ✓ utils.logger")
    except ImportError as e:
        print(f"  ✗ utils.logger: {e}")
        return False

    try:
        from utils.config import load_config, PipelineConfig
        print("  ✓ utils.config")
    except ImportError as e:
        print(f"  ✗ utils.config: {e}")
        return False

    try:
        from utils.retry import create_rate_limiter, create_retry_decorator
        print("  ✓ utils.retry")
    except ImportError as e:
        print(f"  ✗ utils.retry: {e}")
        return False

    try:
        from wix_api.client import WixAPIClient
        print("  ✓ wix_api.client")
    except ImportError as e:
        print(f"  ✗ wix_api.client: {e}")
        return False

    return True


def test_logging():
    """Test that logging setup works."""
    print("\nTesting logging...")

    try:
        from utils.logger import setup_logging
        logger = setup_logging(log_dir="logs", log_level="INFO")
        logger.info("Test log message")
        print("  ✓ Logging setup successful")
        return True
    except Exception as e:
        print(f"  ✗ Logging failed: {e}")
        return False


def test_config_template():
    """Test that configuration files exist."""
    print("\nTesting configuration files...")

    config_dir = Path(__file__).parent.parent / "config"

    files = [
        "credentials.env.template",
        "pipeline_config.yaml",
        "logging.yaml"
    ]

    all_exist = True
    for file in files:
        file_path = config_dir / file
        if file_path.exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} (not found)")
            all_exist = False

    return all_exist


def main():
    """Run all tests."""
    print("=" * 60)
    print("Birdhaus Data Pipeline - Setup Verification")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Dependencies", test_imports()))
    results.append(("Internal Modules", test_internal_modules()))
    results.append(("Logging", test_logging()))
    results.append(("Configuration Files", test_config_template()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "PASSED" if passed else "FAILED"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ All tests passed! The pipeline is ready to use.")
        print("\nNext steps:")
        print("1. Copy config/credentials.env.template to .env")
        print("2. Fill in your Wix API credentials in .env")
        print("3. Run: pip install -e .")
        print("4. Proceed with Phase 2 implementation")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        print("\nTry running: pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
