#!/usr/bin/env python3
"""
Real API test for stock chart creation functionality
Tests the create_stock_chart function with actual API calls to Marketstack
Uses Microsoft (MSFT) stock for testing
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.tools.finance import create_stock_chart

# Access the underlying function from the tool decorator
create_stock_chart_func = create_stock_chart.func


def test_msft_basic_chart():
    """Test basic MSFT chart with real API"""
    print("\n🧪 Testing MSFT Basic Chart (Real API)")
    print("=" * 60)

    try:
        result = create_stock_chart_func(
            symbols=["MSFT"],
            period="daily",
            chart_type="candlestick",
            time_range_days=30,
            include_volume=True,
            technical_indicators=["sma"],
            layout_style="professional",
        )

        print(f"Result type: {type(result)}")
        print(
            f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}"
        )

        if isinstance(result, dict):
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                return False
            elif "message" in result:
                print(f"✅ Success: {result['message']}")
                return True
            else:
                print(f"⚠️  Unexpected result format: {result}")
                return False
        else:
            print(f"⚠️  Unexpected result type: {type(result)}")
            return False

    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_msft_line_chart():
    """Test MSFT line chart with real API"""
    print("\n🧪 Testing MSFT Line Chart (Real API)")
    print("=" * 60)

    try:
        result = create_stock_chart_func(
            symbols=["MSFT"],
            chart_type="line",
            time_range_days=30,
        )

        if isinstance(result, dict):
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                return False
            elif "message" in result:
                print(f"✅ Success: {result['message']}")
                return True
        return False

    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_msft_with_indicators():
    """Test MSFT chart with technical indicators"""
    print("\n🧪 Testing MSFT Chart with Indicators (Real API)")
    print("=" * 60)

    try:
        result = create_stock_chart_func(
            symbols=["MSFT"],
            technical_indicators=["sma", "ema"],
            time_range_days=60,
        )

        if isinstance(result, dict):
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                return False
            elif "message" in result:
                print(f"✅ Success: {result['message']}")
                return True
        return False

    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_msft_intraday():
    """Test MSFT intraday chart"""
    print("\n🧪 Testing MSFT Intraday Chart (Real API)")
    print("=" * 60)

    try:
        result = create_stock_chart_func(
            symbols=["MSFT"],
            period="intraday",
            time_range_days=5,
        )

        if isinstance(result, dict):
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                return False
            elif "message" in result:
                print(f"✅ Success: {result['message']}")
                return True
        return False

    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_multiple_symbols():
    """Test chart with multiple symbols"""
    print("\n🧪 Testing Multiple Symbols Chart (Real API)")
    print("=" * 60)

    try:
        result = create_stock_chart_func(
            symbols=["MSFT", "AAPL"],
            time_range_days=30,
        )

        if isinstance(result, dict):
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                return False
            elif "message" in result:
                print(f"✅ Success: {result['message']}")
                return True
        return False

    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_error_handling():
    """Test error handling with invalid symbol"""
    print("\n🧪 Testing Error Handling (Real API)")
    print("=" * 60)

    try:
        result = create_stock_chart_func(
            symbols=["INVALID_SYMBOL_XYZ123"],
            time_range_days=30,
        )

        if isinstance(result, dict):
            if "error" in result:
                print(f"✅ Error handled correctly: {result['error']}")
                return True
            elif "message" in result:
                print(f"⚠️  Unexpected success with invalid symbol: {result['message']}")
                return False
        return False

    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all real API tests"""
    print("🚀 Stock Chart Real API Test Suite - Microsoft (MSFT)")
    print("=" * 70)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check API key
    api_key = os.getenv("MARKETSTACK_API_KEY")
    if not api_key:
        print("\n⚠️  WARNING: MARKETSTACK_API_KEY not set!")
        print("   This test requires a valid Marketstack API key.")
        print("   Set it in your environment or .env file.")
        print("   Tests will likely fail without a valid API key.\n")
    else:
        print(f"\n✅ MARKETSTACK_API_KEY is set (length: {len(api_key)} chars)")

    results = []

    # Test 1: Basic chart
    results.append(("Basic MSFT Chart", test_msft_basic_chart()))

    # Test 2: Line chart
    results.append(("MSFT Line Chart", test_msft_line_chart()))

    # Test 3: With indicators
    results.append(("MSFT with Indicators", test_msft_with_indicators()))

    # Test 4: Intraday
    results.append(("MSFT Intraday", test_msft_intraday()))

    # Test 5: Multiple symbols
    results.append(("Multiple Symbols", test_multiple_symbols()))

    # Test 6: Error handling
    results.append(("Error Handling", test_error_handling()))

    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Results Summary:")
    print("=" * 70)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<50} {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print("=" * 70)
    print(f"Total: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(passed/len(results)*100):.1f}%")
    print("=" * 70)

    if failed == 0:
        print("\n🎉 All tests passed! Real API integration is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the API integration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
