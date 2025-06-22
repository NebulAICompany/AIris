#!/usr/bin/env python3
"""
Comprehensive Test Suite for Document Verification System
Tests the LLM-based document verification pipeline with various document types.
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List
import subprocess

# Add the backend to the path
sys.path.append(str(Path(__file__).parent / "aiiris_backend"))

from aiiris_backend.pipelines.document_verification import verification_pipeline


class DocumentVerificationTester:
    """Test suite for document verification system"""
    
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🧪 Starting Document Verification System Tests")
        print("=" * 60)
        
        # Test 1: PDF Creation
        self.test_pdf_creation()
        
        # Test 2: Individual document tests
        self.test_suspicious_invoice()
        self.test_clean_receipt()
        
        # Test 3: Edge cases
        self.test_edge_cases()
        
        # Generate report
        self.generate_report()
    
    def test_pdf_creation(self):
        """Test PDF creation from text files"""
        print("\n📄 Testing PDF Creation...")
        
        try:
            script_path = Path("test_documents/create_test_pdfs.py")
            if script_path.exists():
                result = subprocess.run([
                    sys.executable, str(script_path)
                ], capture_output=True, text=True, cwd="test_documents")
                
                if result.returncode == 0:
                    self.log_test("PDF Creation", True, "PDFs created successfully")
                    print("✅ PDF creation successful")
                else:
                    self.log_test("PDF Creation", False, f"PDF creation failed: {result.stderr}")
                    print(f"❌ PDF creation failed: {result.stderr}")
            else:
                self.log_test("PDF Creation", False, "create_test_pdfs.py not found")
                print("❌ create_test_pdfs.py not found")
                
        except Exception as e:
            self.log_test("PDF Creation", False, str(e))
            print(f"❌ PDF creation error: {e}")
    
    def test_suspicious_invoice(self):
        """Test verification of suspicious invoice"""
        print("\n🚨 Testing Suspicious Invoice...")
        
        test_file = Path("test_documents/suspicious_invoice.pdf")
        if not test_file.exists():
            self.log_test("Suspicious Invoice", False, "Test file not found")
            print("❌ suspicious_invoice.pdf not found")
            return
        
        try:
            result = verification_pipeline.verify_document(str(test_file), "auto")
            
            # Expected outcomes for suspicious invoice
            expected_checks = {
                "should_be_rejected": result.get("status") in ["rejected", "review_required"],
                "should_detect_fraud": result.get("stages", {}).get("fraud_analysis", {}).get("risk_level") == "high",
                "should_classify_as_invoice": result.get("verification_type") == "invoice",
                "should_have_low_confidence": result.get("confidence_score", 1.0) < 0.5
            }
            
            passed_checks = sum(expected_checks.values())
            total_checks = len(expected_checks)
            
            # Log detailed results
            print(f"   Status: {result.get('status', 'unknown')}")
            print(f"   Confidence: {result.get('confidence_score', 0):.2f}")
            print(f"   Type: {result.get('verification_type', 'unknown')}")
            
            fraud_analysis = result.get("stages", {}).get("fraud_analysis", {})
            print(f"   Fraud Risk: {fraud_analysis.get('risk_level', 'unknown')}")
            print(f"   Fraud Indicators: {len(fraud_analysis.get('indicators', []))}")
            
            if passed_checks >= 3:  # At least 3 out of 4 checks should pass
                self.log_test("Suspicious Invoice", True, f"Passed {passed_checks}/{total_checks} checks")
                print(f"✅ Suspicious invoice test passed ({passed_checks}/{total_checks})")
            else:
                self.log_test("Suspicious Invoice", False, f"Only passed {passed_checks}/{total_checks} checks")
                print(f"❌ Suspicious invoice test failed ({passed_checks}/{total_checks})")
                
        except Exception as e:
            self.log_test("Suspicious Invoice", False, str(e))
            print(f"❌ Suspicious invoice test error: {e}")
    
    def test_clean_receipt(self):
        """Test verification of clean receipt"""
        print("\n✅ Testing Clean Receipt...")
        
        test_file = Path("test_documents/clean_receipt.pdf")
        if not test_file.exists():
            self.log_test("Clean Receipt", False, "Test file not found")
            print("❌ clean_receipt.pdf not found")
            return
        
        try:
            result = verification_pipeline.verify_document(str(test_file), "auto")
            
            # Expected outcomes for clean receipt
            expected_checks = {
                "should_be_verified": result.get("status") == "verified",
                "should_detect_low_fraud": result.get("stages", {}).get("fraud_analysis", {}).get("risk_level") == "low",
                "should_classify_as_receipt": result.get("verification_type") == "receipt",
                "should_have_high_confidence": result.get("confidence_score", 0.0) > 0.7
            }
            
            passed_checks = sum(expected_checks.values())
            total_checks = len(expected_checks)
            
            # Log detailed results
            print(f"   Status: {result.get('status', 'unknown')}")
            print(f"   Confidence: {result.get('confidence_score', 0):.2f}")
            print(f"   Type: {result.get('verification_type', 'unknown')}")
            
            fraud_analysis = result.get("stages", {}).get("fraud_analysis", {})
            print(f"   Fraud Risk: {fraud_analysis.get('risk_level', 'unknown')}")
            print(f"   Fraud Indicators: {len(fraud_analysis.get('indicators', []))}")
            
            if passed_checks >= 3:  # At least 3 out of 4 checks should pass
                self.log_test("Clean Receipt", True, f"Passed {passed_checks}/{total_checks} checks")
                print(f"✅ Clean receipt test passed ({passed_checks}/{total_checks})")
            else:
                self.log_test("Clean Receipt", False, f"Only passed {passed_checks}/{total_checks} checks")
                print(f"❌ Clean receipt test failed ({passed_checks}/{total_checks})")
                
        except Exception as e:
            self.log_test("Clean Receipt", False, str(e))
            print(f"❌ Clean receipt test error: {e}")
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n⚠️  Testing Edge Cases...")
        
        # Test 1: Non-existent file
        try:
            result = verification_pipeline.verify_document("nonexistent.pdf", "auto")
            if result.get("status") == "error":
                self.log_test("Non-existent File", True, "Properly handled missing file")
                print("✅ Non-existent file handled correctly")
            else:
                self.log_test("Non-existent File", False, "Did not handle missing file")
                print("❌ Non-existent file not handled properly")
        except Exception as e:
            self.log_test("Non-existent File", True, f"Exception caught: {str(e)}")
            print("✅ Non-existent file exception handled")
        
        # Test 2: Manual verification type
        test_file = Path("test_documents/clean_receipt.pdf")
        if test_file.exists():
            try:
                result = verification_pipeline.verify_document(str(test_file), "invoice")
                if result.get("verification_type") == "invoice":
                    self.log_test("Manual Type Override", True, "Manual verification type respected")
                    print("✅ Manual verification type override works")
                else:
                    self.log_test("Manual Type Override", False, "Manual type not respected")
                    print("❌ Manual verification type override failed")
            except Exception as e:
                self.log_test("Manual Type Override", False, str(e))
                print(f"❌ Manual type override error: {e}")
    
    def log_test(self, test_name: str, passed: bool, details: str):
        """Log a test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
        
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": time.time()
        })
    
    def generate_report(self):
        """Generate and display test report"""
        print("\n📊 Test Report")
        print("=" * 60)
        
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        print(f"Success Rate: {(self.passed_tests / self.total_tests * 100):.1f}%" if self.total_tests > 0 else "0%")
        
        print("\n📋 Detailed Results:")
        for result in self.test_results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"  {status} {result['test']}: {result['details']}")
        
        # Save results to file
        report_file = Path("test_verification_report.json")
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": self.total_tests,
                    "passed_tests": self.passed_tests,
                    "success_rate": self.passed_tests / self.total_tests if self.total_tests > 0 else 0
                },
                "results": self.test_results
            }, f, indent=2)
        
        print(f"\n💾 Report saved to: {report_file}")
        
        # Overall result
        if self.passed_tests == self.total_tests:
            print("\n🎉 All tests passed! Document verification system is working correctly.")
        elif self.passed_tests / self.total_tests >= 0.8:
            print("\n✅ Most tests passed. Document verification system is mostly functional.")
        else:
            print("\n⚠️  Many tests failed. Document verification system needs attention.")


def main():
    """Run the test suite"""
    print("AIRIS Document Verification System Test Suite")
    print("=" * 60)
    
    # Check dependencies
    missing_deps = []
    
    try:
        import cv2
    except ImportError:
        missing_deps.append("opencv-python")
    
    try:
        import pytesseract
    except ImportError:
        missing_deps.append("pytesseract")
    
    try:
        import fitz
    except ImportError:
        missing_deps.append("PyMuPDF")
    
    try:
        from openai import OpenAI
    except ImportError:
        missing_deps.append("openai")
    
    if missing_deps:
        print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        print("Please install missing packages and try again.")
        return 1
    
    # Check OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY environment variable not set")
        print("LLM-based analysis may not work properly")
    
    # Run tests
    tester = DocumentVerificationTester()
    tester.run_all_tests()
    
    return 0 if tester.passed_tests == tester.total_tests else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 