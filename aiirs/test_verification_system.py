#!/usr/bin/env python3
"""
Test script for the improved LLM-based document verification system
"""

import os
import sys
from pathlib import Path

# Add the backend to the path
sys.path.append(str(Path(__file__).parent / "aiiris_backend"))

from aiiris_backend.pipelines.document_verification import verification_pipeline


def test_document_verification():
    """Test the document verification system with both test documents"""
    
    print("🔍 Testing LLM-Based Document Verification System")
    print("=" * 60)
    
    # Test documents
    test_docs = [
        {
            "name": "Suspicious Invoice",
            "path": "test_documents/suspicious_invoice.pdf",
            "expected_status": "rejected",
            "type": "invoice"
        },
        {
            "name": "Clean Receipt", 
            "path": "test_documents/clean_receipt.pdf",
            "expected_status": "verified",
            "type": "receipt"
        }
    ]
    
    for doc in test_docs:
        print(f"\n📄 Testing: {doc['name']}")
        print("-" * 40)
        
        if not os.path.exists(doc['path']):
            print(f"❌ File not found: {doc['path']}")
            continue
        
        try:
            # Run verification
            print(f"🔄 Running verification for {doc['name']}...")
            result = verification_pipeline.verify_document(doc['path'], doc['type'])
            
            # Display results
            print(f"📊 Results for {doc['name']}:")
            print(f"   Status: {result['status']}")
            print(f"   Confidence: {result['confidence_score']:.2f}")
            print(f"   Document Type: {result['verification_type']}")
            
            # Show stage results
            if 'stages' in result:
                print(f"   📋 Verification Stages:")
                for stage_name, stage_data in result['stages'].items():
                    if isinstance(stage_data, dict):
                        if 'passed' in stage_data:
                            status = "✅ PASS" if stage_data['passed'] else "❌ FAIL"
                        elif 'valid' in stage_data:
                            status = "✅ PASS" if stage_data['valid'] else "❌ FAIL"
                        elif 'consistent' in stage_data:
                            status = "✅ PASS" if stage_data['consistent'] else "❌ FAIL"
                        elif 'risk_level' in stage_data:
                            risk = stage_data['risk_level']
                            status = f"🔴 HIGH RISK" if risk == 'high' else f"🟡 MED RISK" if risk == 'medium' else "🟢 LOW RISK"
                        else:
                            status = "✅ PASS"
                        
                        print(f"      {stage_name}: {status}")
            
            # Show warnings and errors
            if result.get('warnings'):
                print(f"   ⚠️  Warnings: {len(result['warnings'])}")
                for warning in result['warnings'][:3]:  # Show first 3
                    print(f"      - {warning}")
            
            if result.get('errors'):
                print(f"   ❌ Errors: {len(result['errors'])}")
                for error in result['errors'][:3]:  # Show first 3
                    print(f"      - {error}")
            
            # Check if result matches expectation
            expected = doc['expected_status']
            actual = result['status']
            
            if actual == expected:
                print(f"   ✅ Test PASSED: Expected {expected}, got {actual}")
            else:
                print(f"   ❌ Test FAILED: Expected {expected}, got {actual}")
                
        except Exception as e:
            print(f"   ❌ Verification failed with error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🏁 Document verification testing completed!")


if __name__ == "__main__":
    test_document_verification() 