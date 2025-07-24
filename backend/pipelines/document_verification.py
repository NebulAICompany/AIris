"""
Document Verification Pipeline for AIRIS
Implements comprehensive document verification using LLM-based analysis and Wolfram Alpha mathematical validation.
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import fitz  # PyMuPDF
from backend.libs.logger import get_logger
from openai import OpenAI
import os
import hashlib
import tempfile
import io

# Import Wolfram Alpha tool for mathematical verification
from backend.agents.wolfram_alpha_tool import wolfram_alpha_query

logger = get_logger("DOCUMENT_VERIFICATION")


class DocumentVerificationPipeline:
    """
    Comprehensive document verification pipeline implementing:
    1. Document Quality Control
    2. LLM-Based Document Type Classification
    3. OCR Text Extraction with LLM assistance
    4. LLM-Based Template & Structure Validation
    5. Intelligent Data Consistency Checks
    6. Advanced LLM-Based Fraud Analysis
    """

    def __init__(self):
        self.verification_types = {
            "invoice": "Fatura",
            "receipt": "Fiş/Makbuz",
            "bank_statement": "Banka Ekstresi",
            "payslip": "Maaş Bordrosu",
            "contract": "Sözleşme",
            "tax_declaration": "Vergi Beyannamesi",
            "expense_voucher": "Gider Pusulası",
            "other": "Diğer",
        }

        self.supported_formats = [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".bmp"]

        # Turkish OCR configuration
        self.tesseract_config = r"--oem 3 --psm 6 -l tur+eng"

        # Initialize OpenAI client for LLM analysis
        self.openai_client = OpenAI(
            api_key=os.getenv(
                "OPENAI_API_KEY",
                "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",
            )
        )

    def verify_document(
        self,
        file_path: str,
        verification_type: str = "auto",
        wolfram_enabled: bool = False,
    ) -> Dict[str, Any]:
        """
        Main verification function that orchestrates the entire verification process
        """
        try:
            logger.info(f"Starting verification for: {file_path}")

            results = {
                "file_name": Path(file_path).name,
                "verification_type": verification_type,
                "timestamp": datetime.now().isoformat(),
                "status": "processing",
                "stages": {},
                "confidence_score": 0.0,
                "warnings": [],
                "errors": [],
            }

            # Stage 1: Document Quality Control
            quality_result = self._check_document_quality(file_path)
            results["stages"]["quality_control"] = quality_result

            if not quality_result["passed"]:
                results["status"] = "failed"
                results["errors"].append("Document quality check failed")
                return results

            # Stage 2: LLM-Based Document Type Classification
            if verification_type == "auto":
                classification_result = self._classify_document_type(file_path)
                results["stages"]["classification"] = classification_result
                results["verification_type"] = classification_result.get(
                    "detected_type", "unknown"
                )
            else:
                results["stages"]["classification"] = {
                    "detected_type": verification_type,
                    "confidence": 1.0,
                    "method": "user_specified",
                }

            # Stage 3: OCR Text Extraction with LLM Enhancement
            ocr_result = self._extract_text_ocr(file_path)
            results["stages"]["text_extraction"] = ocr_result

            # Stage 4: LLM-Based Template & Structure Validation
            template_result = self._validate_template_structure(
                file_path, ocr_result["extracted_text"], results["verification_type"]
            )
            results["stages"]["template_validation"] = template_result

            # Stage 5: Intelligent Data Consistency & Cross-checks with Wolfram
            consistency_result = self._check_data_consistency(
                ocr_result["extracted_fields"],
                results["verification_type"],
                wolfram_enabled,
            )
            results["stages"]["data_consistency"] = consistency_result

            # Stage 6: Advanced LLM-Based Fraud Analysis with Wolfram
            fraud_result = self._analyze_fraud_risk(
                file_path, ocr_result, results["verification_type"], wolfram_enabled
            )
            results["stages"]["fraud_analysis"] = fraud_result

            # Calculate overall confidence score
            results["confidence_score"] = self._calculate_confidence_score(
                results["stages"]
            )

            # Determine final status
            if results["confidence_score"] >= 0.8:
                results["status"] = "verified"
            elif results["confidence_score"] >= 0.6:
                results["status"] = "review_required"
                results["warnings"].append(
                    "Low confidence score - manual review recommended"
                )
            else:
                results["status"] = "rejected"
                results["errors"].append("Document failed verification checks")

            logger.info(f"Verification completed with status: {results['status']}")
            return results

        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return {
                "file_name": Path(file_path).name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _check_document_quality(self, file_path: str) -> Dict[str, Any]:
        """Check document quality (clarity, readability, format)"""
        try:
            result = {
                "passed": False,
                "quality_score": 0.0,
                "issues": [],
                "details": {},
            }

            file_ext = Path(file_path).suffix.lower()

            if file_ext == ".pdf":
                # PDF quality check
                doc = fitz.open(file_path)
                if len(doc) == 0:
                    result["issues"].append("PDF has no pages")
                    return result

                page = doc[0]

                # Check if text is extractable
                text = page.get_text()
                if len(text.strip()) > 50:
                    result["details"]["has_text_layer"] = True
                    result["quality_score"] += 0.4
                else:
                    result["details"]["has_text_layer"] = False

                # Check page dimensions
                rect = page.rect
                if rect.width > 200 and rect.height > 200:
                    result["details"]["adequate_size"] = True
                    result["quality_score"] += 0.3
                else:
                    result["issues"].append("Document size too small")

                doc.close()

            elif file_ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
                # Image quality check
                image = cv2.imread(file_path)
                if image is None:
                    result["issues"].append("Could not read image file")
                    return result

                height, width = image.shape[:2]

                # Check image dimensions
                if width >= 800 and height >= 600:
                    result["details"]["adequate_resolution"] = True
                    result["quality_score"] += 0.3
                else:
                    result["issues"].append("Image resolution too low")

                # Check image sharpness using Laplacian variance
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

                if laplacian_var > 100:
                    result["details"]["adequate_sharpness"] = True
                    result["quality_score"] += 0.4
                else:
                    result["issues"].append("Image appears blurry")

                result["details"]["laplacian_variance"] = float(laplacian_var)

            # File size check
            file_size = os.path.getsize(file_path)
            if file_size > 1024:  # At least 1KB
                result["quality_score"] += 0.3
            else:
                result["issues"].append("File size too small")

            result["passed"] = result["quality_score"] >= 0.6
            result["details"]["file_size_bytes"] = file_size

            return result

        except Exception as e:
            logger.error(f"Quality check failed: {str(e)}")
            return {
                "passed": False,
                "quality_score": 0.0,
                "issues": [f"Quality check error: {str(e)}"],
                "details": {},
            }

    def _classify_document_type(self, file_path: str) -> Dict[str, Any]:
        """Classify document type using LLM-based intelligent analysis"""
        try:
            # Extract text for classification
            text = self._extract_text_simple(file_path)

            if not text or len(text.strip()) < 20:
                return {
                    "detected_type": "unknown",
                    "confidence": 0.0,
                    "error": "Insufficient text content",
                    "method": "llm_analysis",
                }

            # Create LLM prompt for document classification
            classification_prompt = f"""
            Analyze the following Turkish document text and classify its type. Consider the content, structure, and terminology used.

            Document Text:
            {text[:2000]}

            Available document types:
            - invoice: Fatura (contains items, amounts, tax info, seller/buyer details)
            - receipt: Fiş/Makbuz (retail/store purchase receipt)
            - bank_statement: Banka Ekstresi (account transactions, balances)
            - payslip: Maaş Bordrosu (salary details, deductions)
            - contract: Sözleşme (agreement terms, parties, signatures)
            - tax_declaration: Vergi Beyannamesi (tax filing documents)
            - expense_voucher: Gider Pusulası (expense claims)
            - other: Other financial document

            Respond with a JSON object containing:
            {{
                "document_type": "detected_type",
                "confidence": 0.95,
                "reasoning": "Brief explanation of why this classification was chosen",
                "key_indicators": ["list", "of", "key", "terms", "found"]
            }}

            Be very careful to analyze the actual content, not just look for keywords.
            """

            llm_response = self._get_llm_response(classification_prompt)

            try:
                # Parse LLM response using robust extraction
                result = self._extract_json_from_response(llm_response)

                return {
                    "detected_type": result.get("document_type", "unknown"),
                    "confidence": min(max(result.get("confidence", 0.0), 0.0), 1.0),
                    "reasoning": result.get("reasoning", ""),
                    "key_indicators": result.get("key_indicators", []),
                    "method": "llm_analysis",
                }

            except json.JSONDecodeError:
                # Fallback parsing if JSON is malformed
                logger.warning(
                    "LLM classification response was not valid JSON, attempting fallback parsing"
                )
                return self._fallback_classification(text)

        except Exception as e:
            logger.error(f"LLM classification failed: {str(e)}")
            return self._fallback_classification(text)

    def _fallback_classification(self, text: str) -> Dict[str, Any]:
        """Simple fallback classification"""
        text_lower = text.lower()
        if "fatura" in text_lower or "invoice" in text_lower:
            return {"detected_type": "invoice", "confidence": 0.7, "method": "fallback"}
        elif "fiş" in text_lower or "makbuz" in text_lower:
            return {"detected_type": "receipt", "confidence": 0.7, "method": "fallback"}
        elif "bordro" in text_lower or "maaş" in text_lower:
            return {"detected_type": "payslip", "confidence": 0.7, "method": "fallback"}
        else:
            return {"detected_type": "other", "confidence": 0.5, "method": "fallback"}

    def _extract_text_ocr(self, file_path: str) -> Dict[str, Any]:
        """Extract text using OCR and identify key fields with LLM assistance"""
        try:
            text = ""
            extracted_fields = {}

            file_ext = Path(file_path).suffix.lower()

            if file_ext == ".pdf":
                # First try to extract text directly from PDF
                doc = fitz.open(file_path)
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text += page.get_text() + "\n"
                doc.close()

                # If no text found, convert to image and OCR
                if len(text.strip()) < 50:
                    text = self._ocr_pdf_as_image(file_path)

            elif file_ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
                text = pytesseract.image_to_string(
                    Image.open(file_path), config=self.tesseract_config
                )

            # Extract key fields using combined approach
            extracted_fields = self._extract_key_fields(text)

            # Add full text to extracted fields for LLM analysis
            extracted_fields["full_text"] = text

            return {
                "extracted_text": text,
                "extracted_fields": extracted_fields,
                "text_length": len(text),
                "confidence": self._estimate_ocr_confidence(text),
            }

        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return {
                "extracted_text": "",
                "extracted_fields": {},
                "text_length": 0,
                "confidence": 0.0,
                "error": str(e),
            }

    def _extract_key_fields(self, text: str) -> Dict[str, Any]:
        """Extract key fields using both regex patterns and LLM assistance"""
        fields = {}

        # Start with regex-based extraction for basic fields
        fields.update(self._regex_field_extraction(text))

        # Use LLM for enhanced field extraction if text is substantial
        if len(text.strip()) > 200:
            try:
                llm_fields = self._llm_field_extraction(text)
                # Merge LLM results with regex results
                for key, value in llm_fields.items():
                    if value and (key not in fields or not fields[key]):
                        fields[key] = value
            except Exception as e:
                logger.warning(
                    f"LLM field extraction failed, using regex only: {str(e)}"
                )

        return fields

    def _regex_field_extraction(self, text: str) -> Dict[str, Any]:
        """Traditional regex-based field extraction"""
        fields = {}

        # Date patterns
        date_patterns = [
            r"\d{2}[./]\d{2}[./]\d{4}",
            r"\d{2}[./]\d{2}[./]\d{2}",
            r"\d{1,2}\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4}",
        ]

        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, text, re.IGNORECASE))

        if dates:
            fields["dates"] = dates

        # Amount patterns (Turkish Lira and other currencies)
        amount_patterns = [
            r"\d+[.,]\d{2}\s*₺",
            r"\d+[.,]\d{2}\s*TL",
            r"\d+[.,]\d{2}\s*USD",
            r"\d+[.,]\d{2}\s*EUR",
            r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})",
        ]

        amounts = []
        for pattern in amount_patterns:
            amounts.extend(re.findall(pattern, text, re.IGNORECASE))

        if amounts:
            fields["amounts"] = amounts

        # Tax number patterns
        tax_patterns = [
            r"VKN\s*:?\s*(\d{10})",
            r"Vergi\s+No\s*:?\s*(\d{10})",
            r"Tax\s+No\s*:?\s*(\d{10})",
        ]

        tax_numbers = []
        for pattern in tax_patterns:
            tax_numbers.extend(re.findall(pattern, text, re.IGNORECASE))

        if tax_numbers:
            fields["tax_numbers"] = tax_numbers

        # IBAN patterns
        iban_pattern = r"TR\d{2}\s?(?:\d{4}\s?){5}\d{2}"
        ibans = re.findall(iban_pattern, text, re.IGNORECASE)

        if ibans:
            fields["ibans"] = ibans

        return fields

    def _llm_field_extraction(self, text: str) -> Dict[str, Any]:
        """LLM-assisted field extraction for better accuracy"""
        extraction_prompt = f"""
        Extract key information from this Turkish financial document:

        Document Text:
        {text[:2000]}

        Extract the following fields if present:
        - dates: All dates in the document
        - amounts: All monetary amounts
        - tax_numbers: Turkish tax numbers (10 digits)
        - ibans: Turkish IBAN numbers
        - company_names: Company or business names
        - document_numbers: Invoice numbers, receipt numbers, etc.

        Respond with a JSON object:
        {{
            "dates": ["15.03.2024", "16.03.2024"],
            "amounts": ["144.14 TL", "25.000,00 TL"],
            "tax_numbers": ["1234567890"],
            "ibans": ["TR12 3456 7890 1234 5678 9012 34"],
            "company_names": ["ABC Company Ltd."],
            "document_numbers": ["F-2024-001"]
        }}

        Only include fields that are actually present in the document.
        """

        try:
            llm_response = self._get_llm_response(extraction_prompt)
            result = self._extract_json_from_response(llm_response)

            # Clean and validate extracted fields
            cleaned_result = {}
            for key, value in result.items():
                if isinstance(value, list) and value:
                    # Remove empty strings and clean up
                    cleaned_value = [
                        str(v).strip() for v in value if v and str(v).strip()
                    ]
                    if cleaned_value:
                        cleaned_result[key] = cleaned_value

            return cleaned_result

        except Exception as e:
            logger.warning(f"LLM field extraction failed: {str(e)}")
            return {}

    def _validate_template_structure(
        self, file_path: str, text: str, doc_type: str
    ) -> Dict[str, Any]:
        """Validate document structure and format compliance using LLM analysis"""
        try:
            if not text or len(text.strip()) < 50:
                return {
                    "valid": False,
                    "score": 0.0,
                    "checks": {},
                    "issues": ["Insufficient text content for validation"],
                }

            # Create LLM prompt for template validation
            validation_prompt = f"""
            Analyze the following {doc_type} document for structural validity and compliance with standard formats.

            Document Type: {doc_type}
            Document Text:
            {text[:3000]}

            For a valid {doc_type}, check for:
            - Required fields and information
            - Date formats and consistency
            - Amount formats and calculations
            - Tax information (if applicable)
            - Company/entity information
            - Legal compliance elements
            - Professional formatting

            Respond with a JSON object:
            {{
                "is_valid": true,
                "confidence_score": 0.85,
                "missing_fields": ["list of missing required fields"],
                "format_issues": ["list of format problems"],
                "calculation_errors": ["math or calculation errors found"],
                "date_issues": ["date-related problems"],
                "overall_assessment": "Brief summary of document validity"
            }}

            Be thorough in checking for inconsistencies, missing information, and format issues.
            """

            llm_response = self._get_llm_response(validation_prompt)

            try:
                result = self._extract_json_from_response(llm_response)

                # Calculate score based on LLM analysis
                base_score = result.get("confidence_score", 0.5)

                # Reduce score for each issue type
                missing_fields = result.get("missing_fields", [])
                format_issues = result.get("format_issues", [])
                calculation_errors = result.get("calculation_errors", [])
                date_issues = result.get("date_issues", [])

                penalty = (
                    len(missing_fields) * 0.1
                    + len(format_issues) * 0.05
                    + len(calculation_errors) * 0.15
                    + len(date_issues) * 0.1
                )

                final_score = max(0.0, base_score - penalty)

                # Compile all issues
                all_issues = (
                    missing_fields + format_issues + calculation_errors + date_issues
                )

                return {
                    "valid": result.get("is_valid", False) and final_score >= 0.6,
                    "score": final_score,
                    "checks": {
                        "has_required_fields": len(missing_fields) == 0,
                        "proper_formatting": len(format_issues) == 0,
                        "correct_calculations": len(calculation_errors) == 0,
                        "valid_dates": len(date_issues) == 0,
                    },
                    "issues": all_issues,
                    "assessment": result.get("overall_assessment", ""),
                }

            except json.JSONDecodeError:
                logger.warning(
                    "Template validation LLM response was not valid JSON, falling back to simple validation"
                )
                return self._simple_template_validation(text, doc_type)

        except Exception as e:
            logger.error(f"LLM template validation failed: {str(e)}")
            return self._simple_template_validation(text, doc_type)

    def _simple_template_validation(self, text: str, doc_type: str) -> Dict[str, Any]:
        """Fallback simple validation"""
        score = 0.5
        issues = []

        # Basic checks
        if len(text.strip()) > 100:
            score += 0.2
        else:
            issues.append("Insufficient content")

        if re.search(r"\d+[.,]\d{2}", text):  # Money amounts
            score += 0.2
        else:
            issues.append("No monetary amounts found")

        if re.search(r"\d{2}[./]\d{2}[./]\d{4}", text):  # Dates
            score += 0.1
        else:
            issues.append("No valid dates found")

        return {
            "valid": score >= 0.6,
            "score": score,
            "checks": {"basic_validation": True},
            "issues": issues,
        }

    def _check_data_consistency(
        self,
        extracted_fields: Dict[str, Any],
        doc_type: str,
        wolfram_enabled: bool = False,
    ) -> Dict[str, Any]:
        """Check data consistency and cross-validate fields using LLM analysis"""
        try:
            # Get the full text again for consistency checking
            text = extracted_fields.get("full_text", "")

            if not text or len(text.strip()) < 50:
                return {
                    "consistent": False,
                    "score": 0.0,
                    "checks": {},
                    "issues": ["Insufficient text for consistency analysis"],
                }

            # Create LLM prompt for data consistency analysis
            consistency_prompt = f"""
            Analyze this {doc_type} document for data consistency and logical coherence.

            Document Text:
            {text[:3000]}

            Check for:
            1. Date consistency (are all dates logical and in proper sequence?)
            2. Mathematical accuracy (do calculations add up correctly?)
            3. Amount reasonableness (are amounts realistic for this document type?)
            4. Cross-field validation (do related fields match each other?)
            5. Business logic compliance (does the content make business sense?)
            6. Tax calculations (if applicable, are tax amounts correct?)
            7. Currency and formatting consistency

            Respond with a JSON object:
            {{
                "is_consistent": true,
                "consistency_score": 0.85,
                "date_issues": ["list of date-related inconsistencies"],
                "calculation_errors": ["list of mathematical errors"],
                "amount_issues": ["list of unrealistic or problematic amounts"],
                "logical_inconsistencies": ["list of business logic violations"],
                "overall_assessment": "Summary of consistency analysis"
            }}

            Be very thorough in checking mathematical calculations and logical relationships.
            """

            llm_response = self._get_llm_response(consistency_prompt)

            try:
                result = self._extract_json_from_response(llm_response)

                # Calculate consistency score based on issues found
                base_score = result.get("consistency_score", 0.5)

                date_issues = result.get("date_issues", [])
                calculation_errors = result.get("calculation_errors", [])
                amount_issues = result.get("amount_issues", [])
                logical_issues = result.get("logical_inconsistencies", [])

                # Apply penalties for different types of issues
                penalty = (
                    len(date_issues) * 0.1
                    + len(calculation_errors) * 0.2  # Math errors are serious
                    + len(amount_issues) * 0.1
                    + len(logical_issues) * 0.15
                )

                final_score = max(0.0, base_score - penalty)

                # Compile all issues
                all_issues = (
                    date_issues + calculation_errors + amount_issues + logical_issues
                )

                # Add Wolfram Alpha mathematical verification if enabled
                wolfram_checks = {}
                wolfram_issues = []
                if wolfram_enabled and extracted_fields:
                    wolfram_analysis = self._perform_wolfram_mathematical_verification(
                        extracted_fields, text
                    )
                    wolfram_checks = wolfram_analysis.get("checks", {})
                    wolfram_issues = wolfram_analysis.get("issues", [])

                    # Adjust score based on Wolfram findings
                    if wolfram_analysis.get("mathematical_errors_found", 0) > 0:
                        final_score -= (
                            0.2  # Significant penalty for mathematical errors
                        )

                    all_issues.extend(wolfram_issues)

                return {
                    "consistent": result.get("is_consistent", False)
                    and final_score >= 0.6,
                    "score": max(0.0, final_score),
                    "checks": {
                        "dates_consistent": len(date_issues) == 0,
                        "calculations_correct": len(calculation_errors) == 0,
                        "amounts_reasonable": len(amount_issues) == 0,
                        "logically_coherent": len(logical_issues) == 0,
                        **wolfram_checks,
                    },
                    "issues": all_issues,
                    "assessment": result.get("overall_assessment", ""),
                    "wolfram_analysis": wolfram_analysis if wolfram_enabled else None,
                }

            except json.JSONDecodeError:
                logger.warning(
                    "Data consistency LLM response was not valid JSON, falling back to simple check"
                )
                return self._simple_consistency_check(extracted_fields)

        except Exception as e:
            logger.error(f"LLM data consistency check failed: {str(e)}")
            return self._simple_consistency_check(extracted_fields)

    def _simple_consistency_check(
        self, extracted_fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback simple consistency check"""
        score = 0.7
        issues = []
        checks = {}

        # Basic field presence checks
        if "dates" in extracted_fields and extracted_fields["dates"]:
            checks["has_dates"] = True
        else:
            issues.append("No dates found")
            score -= 0.2

        if "amounts" in extracted_fields and extracted_fields["amounts"]:
            checks["has_amounts"] = True
        else:
            issues.append("No amounts found")
            score -= 0.2

        return {
            "consistent": score >= 0.5,
            "score": max(0.0, score),
            "checks": checks,
            "issues": issues,
        }

    def _analyze_fraud_risk(
        self,
        file_path: str,
        ocr_result: Dict[str, Any],
        doc_type: str,
        wolfram_enabled: bool = False,
    ) -> Dict[str, Any]:
        """Analyze document for fraud risk indicators using LLM-based intelligent analysis"""
        try:
            text = ocr_result.get("extracted_text", "")

            if not text or len(text.strip()) < 50:
                return {
                    "risk_level": "unknown",
                    "risk_score": 0.5,
                    "indicators": ["Insufficient text for fraud analysis"],
                    "checks": {},
                }

            # Create LLM prompt for fraud analysis
            fraud_prompt = f"""
            Analyze this {doc_type} document for potential fraud indicators and suspicious patterns.

            Document Text:
            {text[:3000]}

            Look for fraud indicators such as:
            1. Suspicious text patterns (mentions of editing software, fake, duplicate, template, etc.)
            2. Unrealistic amounts or values
            3. Invalid or suspicious dates (impossible dates, future dates for past transactions)
            4. Inconsistent formatting or unprofessional presentation
            5. Suspicious company names or contact information
            6. Mathematical inconsistencies or calculation errors
            7. Missing or invalid required information (tax numbers, IBANs, etc.)
            8. Threatening or unrealistic terms
            9. Poor grammar or suspicious language patterns
            10. Any other red flags that suggest document manipulation or fraud

            Respond with a JSON object:
            {{
                "risk_level": "low",
                "risk_score": 0.25,
                "fraud_indicators": ["list", "of", "specific", "fraud", "indicators", "found"],
                "suspicious_patterns": ["list", "of", "suspicious", "text", "patterns"],
                "unrealistic_elements": ["list", "of", "unrealistic", "amounts", "dates", "etc"],
                "assessment": "Overall fraud risk assessment explanation"
            }}

            Be very thorough in detecting subtle fraud indicators and suspicious patterns.
            """

            llm_response = self._get_llm_response(fraud_prompt)

            try:
                result = self._extract_json_from_response(llm_response)

                # Extract fraud analysis results
                risk_level = result.get("risk_level", "medium")
                base_risk_score = result.get("risk_score", 0.5)
                fraud_indicators = result.get("fraud_indicators", [])
                suspicious_patterns = result.get("suspicious_patterns", [])
                unrealistic_elements = result.get("unrealistic_elements", [])

                # Adjust risk score based on number of indicators
                indicator_penalty = len(fraud_indicators) * 0.1
                pattern_penalty = len(suspicious_patterns) * 0.05
                unrealistic_penalty = len(unrealistic_elements) * 0.1

                final_risk_score = min(
                    1.0,
                    base_risk_score
                    + indicator_penalty
                    + pattern_penalty
                    + unrealistic_penalty,
                )

                # Check OCR confidence as additional factor
                ocr_confidence = ocr_result.get("confidence", 1.0)
                if ocr_confidence < 0.7:
                    fraud_indicators.append(
                        "Low OCR confidence - possible image manipulation"
                    )
                    final_risk_score += 0.1

                # Determine final risk level
                if final_risk_score >= 0.7:
                    final_risk_level = "high"
                elif final_risk_score >= 0.4:
                    final_risk_level = "medium"
                else:
                    final_risk_level = "low"

                # Combine all indicators
                all_indicators = (
                    fraud_indicators + suspicious_patterns + unrealistic_elements
                )

                # Add Wolfram Alpha advanced mathematical fraud detection if enabled
                wolfram_fraud_checks = {}
                if wolfram_enabled:
                    wolfram_fraud_analysis = self._perform_wolfram_fraud_detection(
                        text, ocr_result.get("extracted_fields", {})
                    )
                    wolfram_fraud_checks = wolfram_fraud_analysis.get("checks", {})

                    # Add Wolfram-detected indicators
                    wolfram_indicators = wolfram_fraud_analysis.get("indicators", [])
                    all_indicators.extend(wolfram_indicators)

                    # Adjust risk score based on Wolfram mathematical fraud indicators
                    if wolfram_fraud_analysis.get("mathematical_fraud_score", 0) > 0.3:
                        final_risk_score += (
                            0.3  # Significant increase for mathematical fraud
                        )

                final_risk_score = min(1.0, final_risk_score)

                # Re-determine risk level with Wolfram input
                if final_risk_score >= 0.7:
                    final_risk_level = "high"
                elif final_risk_score >= 0.4:
                    final_risk_level = "medium"
                else:
                    final_risk_level = "low"

                return {
                    "risk_level": final_risk_level,
                    "risk_score": final_risk_score,
                    "indicators": all_indicators,
                    "checks": {
                        "fraud_indicators_found": len(fraud_indicators),
                        "suspicious_patterns_found": len(suspicious_patterns),
                        "unrealistic_elements_found": len(unrealistic_elements),
                        "ocr_confidence": ocr_confidence,
                        **wolfram_fraud_checks,
                    },
                    "assessment": result.get("assessment", ""),
                    "wolfram_fraud_analysis": (
                        wolfram_fraud_analysis if wolfram_enabled else None
                    ),
                }

            except json.JSONDecodeError:
                logger.warning(
                    "Fraud analysis LLM response was not valid JSON, falling back to simple analysis"
                )
                return self._simple_fraud_analysis(text, ocr_result)

        except Exception as e:
            logger.error(f"LLM fraud analysis failed: {str(e)}")
            return self._simple_fraud_analysis(
                ocr_result.get("extracted_text", ""), ocr_result
            )

    def _simple_fraud_analysis(
        self, text: str, ocr_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback simple fraud analysis"""
        risk_score = 0.0
        indicators = []

        text_lower = text.lower()

        # Simple pattern detection
        suspicious_words = [
            "photoshop",
            "fake",
            "template",
            "duplicate",
            "copy",
            "edited",
            "modified",
        ]
        for word in suspicious_words:
            if word in text_lower:
                indicators.append(f"Suspicious text pattern: '{word}'")
                risk_score += 0.15

        # Check OCR confidence
        ocr_confidence = ocr_result.get("confidence", 1.0)
        if ocr_confidence < 0.7:
            indicators.append("Low OCR confidence")
            risk_score += 0.1

        # Determine risk level
        if risk_score >= 0.3:
            risk_level = "high"
        elif risk_score >= 0.15:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_level": risk_level,
            "risk_score": min(1.0, risk_score),
            "indicators": indicators,
            "checks": {"ocr_confidence": ocr_confidence},
        }

    # Helper methods
    def _extract_text_simple(self, file_path: str) -> str:
        """Simple text extraction for classification"""
        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext == ".pdf":
                doc = fitz.open(file_path)
                text = ""
                for page_num in range(min(3, len(doc))):  # First 3 pages only
                    page = doc[page_num]
                    text += page.get_text()
                doc.close()
                return text

            elif file_ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
                return pytesseract.image_to_string(
                    Image.open(file_path), config=self.tesseract_config
                )

            return ""

        except Exception as e:
            logger.error(f"Simple text extraction failed: {str(e)}")
            return ""

    def _estimate_ocr_confidence(self, text: str) -> float:
        """Estimate OCR confidence based on text characteristics"""
        if not text:
            return 0.0

        # Simple heuristics for confidence estimation
        confidence = 1.0

        # Check for common OCR errors
        error_indicators = ["|||", "###", "???", "...", "   "]
        for indicator in error_indicators:
            if indicator in text:
                confidence *= 0.9

        # Check character ratio
        total_chars = len(text)
        if total_chars == 0:
            return 0.0

        # Count non-alphanumeric characters
        non_alnum = sum(1 for c in text if not c.isalnum() and not c.isspace())
        non_alnum_ratio = non_alnum / total_chars

        if non_alnum_ratio > 0.3:
            confidence *= 0.8

        return min(confidence, 1.0)

    def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM for document analysis"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert document verification analyst specializing in Turkish financial documents. Always respond with only valid JSON in the exact format requested, without any additional text or explanations.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for consistent results
                max_tokens=2000,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM API call failed: {str(e)}")
            raise e

    def _extract_json_from_response(self, response: str) -> dict:
        """Extract valid JSON from LLM response that may contain extra text"""
        try:
            # First, try direct parsing
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # If direct parsing fails, try to extract JSON from the response
        try:
            # Look for JSON-like content between braces
            import re

            # Find JSON objects in the response
            json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
            matches = re.findall(json_pattern, response, re.DOTALL)

            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

            # If no valid JSON found, try extracting from code blocks
            code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
            code_matches = re.findall(
                code_block_pattern, response, re.DOTALL | re.IGNORECASE
            )

            for match in code_matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

            # If still no valid JSON, try line-by-line extraction
            lines = response.split("\n")
            json_lines = []
            in_json = False

            for line in lines:
                stripped = line.strip()
                if stripped.startswith("{"):
                    in_json = True
                    json_lines = [stripped]
                elif in_json:
                    json_lines.append(stripped)
                    if stripped.endswith("}"):
                        try:
                            potential_json = "\n".join(json_lines)
                            return json.loads(potential_json)
                        except json.JSONDecodeError:
                            in_json = False
                            json_lines = []

            # If all extraction attempts fail, log the response and raise an error
            logger.warning(
                f"Could not extract valid JSON from LLM response: {response[:200]}..."
            )
            raise json.JSONDecodeError("No valid JSON found in response", response, 0)

        except Exception as e:
            logger.error(f"JSON extraction failed: {str(e)}")
            raise json.JSONDecodeError("JSON extraction failed", response, 0)

    def _calculate_confidence_score(self, stages: Dict[str, Any]) -> float:
        """Calculate overall confidence score from all verification stages"""
        weights = {
            "quality_control": 0.2,
            "classification": 0.15,
            "text_extraction": 0.2,
            "template_validation": 0.2,
            "data_consistency": 0.15,
            "fraud_analysis": 0.1,
        }

        total_score = 0.0
        total_weight = 0.0

        for stage, weight in weights.items():
            if stage in stages:
                stage_data = stages[stage]

                # Extract score based on stage type
                if stage == "quality_control":
                    score = stage_data.get("quality_score", 0.0)
                elif stage == "classification":
                    score = stage_data.get("confidence", 0.0)
                elif stage == "text_extraction":
                    score = stage_data.get("confidence", 0.0)
                elif stage == "template_validation":
                    score = stage_data.get("score", 0.0)
                elif stage == "data_consistency":
                    score = stage_data.get("score", 0.0)
                elif stage == "fraud_analysis":
                    # Invert fraud risk score (higher risk = lower confidence)
                    risk_score = stage_data.get("risk_score", 0.0)
                    score = max(0.0, 1.0 - risk_score)
                else:
                    score = 0.0

                total_score += score * weight
                total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def _ocr_pdf_as_image(self, file_path: str) -> str:
        """Convert PDF to image and perform OCR"""
        try:
            doc = fitz.open(file_path)
            text = ""

            for page_num in range(min(5, len(doc))):  # First 5 pages
                page = doc[page_num]
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")

                # Convert to PIL Image
                img = Image.open(io.BytesIO(img_data))

                # Perform OCR
                page_text = pytesseract.image_to_string(
                    img, config=self.tesseract_config
                )
                text += page_text + "\n"

            doc.close()
            return text

        except Exception as e:
            logger.error(f"PDF OCR failed: {str(e)}")
            return ""

    def _perform_wolfram_mathematical_verification(
        self, extracted_fields: Dict[str, Any], text: str
    ) -> Dict[str, Any]:
        """Use Wolfram Alpha to verify mathematical calculations and consistency"""
        try:
            logger.info("Starting Wolfram Alpha mathematical verification")

            verification_results = {
                "checks": {},
                "issues": [],
                "calculations_verified": 0,
                "mathematical_errors_found": 0,
                "wolfram_responses": [],
            }

            # Extract numerical values for verification
            amounts = extracted_fields.get("amounts", [])

            if not amounts:
                verification_results["issues"].append(
                    "No monetary amounts found for Wolfram verification"
                )
                return verification_results

            # Process amounts and perform mathematical validations
            processed_amounts = []
            for amount in amounts:
                # Clean and extract numeric value
                cleaned_amount = re.sub(r"[^\d.,]", "", str(amount))
                if cleaned_amount:
                    # Convert to decimal format for Wolfram
                    if "," in cleaned_amount:
                        # Assume Turkish format (1.234,56)
                        cleaned_amount = cleaned_amount.replace(".", "").replace(
                            ",", "."
                        )

                    try:
                        numeric_value = float(cleaned_amount)
                        processed_amounts.append(numeric_value)
                    except ValueError:
                        continue

            if len(processed_amounts) >= 2:
                # Verify mathematical relationships
                verification_results.update(
                    self._verify_mathematical_relationships(processed_amounts, text)
                )

            # Check for percentage calculations
            verification_results.update(self._verify_percentage_calculations(text))

            # Verify tax calculations if present
            verification_results.update(
                self._verify_tax_calculations(text, processed_amounts)
            )

            # Set verification flags
            verification_results["checks"]["wolfram_mathematical_verification"] = True
            verification_results["checks"]["calculations_mathematically_correct"] = (
                verification_results["mathematical_errors_found"] == 0
            )

            logger.info(
                f"Wolfram verification completed: {verification_results['calculations_verified']} calculations verified, {verification_results['mathematical_errors_found']} errors found"
            )

            return verification_results

        except Exception as e:
            logger.error(f"Wolfram mathematical verification failed: {str(e)}")
            return {
                "checks": {"wolfram_verification_failed": True},
                "issues": [f"Wolfram verification error: {str(e)}"],
                "calculations_verified": 0,
                "mathematical_errors_found": 0,
                "wolfram_responses": [],
            }

    def _verify_mathematical_relationships(
        self, amounts: List[float], text: str
    ) -> Dict[str, Any]:
        """Verify mathematical relationships between amounts using Wolfram"""
        results = {
            "calculations_verified": 0,
            "mathematical_errors_found": 0,
            "issues": [],
            "wolfram_responses": [],
        }

        try:
            # Check if amounts could represent a subtotal/tax/total relationship
            if len(amounts) >= 3:
                sorted_amounts = sorted(amounts)
                largest = sorted_amounts[-1]
                potential_subtotal = sorted_amounts[-2]
                potential_tax = sorted_amounts[-3]

                # Verify if largest = subtotal + tax
                query = f"Is {largest} equal to {potential_subtotal} + {potential_tax}?"
                wolfram_response = wolfram_alpha_query(query)
                results["wolfram_responses"].append(
                    {"query": query, "response": wolfram_response}
                )
                results["calculations_verified"] += 1

                if (
                    "true" in wolfram_response.lower()
                    or "yes" in wolfram_response.lower()
                ):
                    logger.info("Wolfram confirmed mathematical relationship")
                elif (
                    "false" in wolfram_response.lower()
                    or "no" in wolfram_response.lower()
                ):
                    results["mathematical_errors_found"] += 1
                    results["issues"].append(
                        f"Mathematical inconsistency: {largest} ≠ {potential_subtotal} + {potential_tax}"
                    )

            return results

        except Exception as e:
            logger.warning(f"Mathematical relationship verification failed: {str(e)}")
            return results

    def _verify_percentage_calculations(self, text: str) -> Dict[str, Any]:
        """Verify percentage calculations using Wolfram Alpha"""
        results = {
            "calculations_verified": 0,
            "mathematical_errors_found": 0,
            "issues": [],
            "wolfram_responses": [],
        }

        try:
            # Look for percentage patterns (Turkish VAT is typically 18% or 8%)
            percentage_patterns = [
                r"%\s*(\d+(?:[.,]\d+)?)",
                r"(\d+(?:[.,]\d+)?)\s*%",
                r"KDV\s*%?\s*(\d+(?:[.,]\d+)?)",
                r"(\d+(?:[.,]\d+)?)\s*KDV",
            ]

            percentages = []
            for pattern in percentage_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        # Handle Turkish decimal format
                        cleaned = match.replace(",", ".")
                        percentage = float(cleaned)
                        if 0 < percentage <= 100:  # Valid percentage range
                            percentages.append(percentage)
                    except ValueError:
                        continue

            # Verify common Turkish VAT rates
            for percentage in percentages:
                if percentage not in [8, 18, 1, 10]:  # Common Turkish VAT rates
                    query = f"Is {percentage}% a valid Turkish VAT rate?"
                    wolfram_response = wolfram_alpha_query(query)
                    results["wolfram_responses"].append(
                        {"query": query, "response": wolfram_response}
                    )
                    results["calculations_verified"] += 1

                    # Check if response indicates this is unusual
                    if (
                        "no" in wolfram_response.lower()
                        or "invalid" in wolfram_response.lower()
                    ):
                        results["issues"].append(
                            f"Unusual VAT rate detected: {percentage}%"
                        )

            return results

        except Exception as e:
            logger.warning(f"Percentage calculation verification failed: {str(e)}")
            return results

    def _verify_tax_calculations(
        self, text: str, amounts: List[float]
    ) -> Dict[str, Any]:
        """Verify tax calculations using Wolfram Alpha"""
        results = {
            "calculations_verified": 0,
            "mathematical_errors_found": 0,
            "issues": [],
            "wolfram_responses": [],
        }

        try:
            # Common Turkish VAT rates
            common_vat_rates = [0.08, 0.18, 0.01, 0.10]  # 8%, 18%, 1%, 10%

            # Check if any amount relationships match VAT calculations
            for i, base_amount in enumerate(amounts):
                for j, total_amount in enumerate(amounts):
                    if i != j and total_amount > base_amount:
                        # Calculate implied tax rate
                        tax_amount = total_amount - base_amount
                        if base_amount > 0:
                            implied_rate = tax_amount / base_amount

                            # Check if this matches a standard VAT rate
                            for vat_rate in common_vat_rates:
                                if abs(implied_rate - vat_rate) < 0.001:  # Close match
                                    # Verify calculation with Wolfram
                                    expected_total = base_amount * (1 + vat_rate)
                                    query = f"What is {base_amount} + ({base_amount} * {vat_rate})?"
                                    wolfram_response = wolfram_alpha_query(query)
                                    results["wolfram_responses"].append(
                                        {"query": query, "response": wolfram_response}
                                    )
                                    results["calculations_verified"] += 1

                                    # Extract numerical result from Wolfram
                                    wolfram_result = (
                                        self._extract_number_from_wolfram_response(
                                            wolfram_response
                                        )
                                    )
                                    if (
                                        wolfram_result
                                        and abs(wolfram_result - total_amount) > 0.01
                                    ):
                                        results["mathematical_errors_found"] += 1
                                        results["issues"].append(
                                            f"VAT calculation error: Expected {wolfram_result}, found {total_amount}"
                                        )

            return results

        except Exception as e:
            logger.warning(f"Tax calculation verification failed: {str(e)}")
            return results

    def _perform_wolfram_fraud_detection(
        self, text: str, extracted_fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use Wolfram Alpha for advanced mathematical fraud detection"""
        try:
            logger.info("Starting Wolfram Alpha fraud detection")

            fraud_analysis = {
                "checks": {},
                "indicators": [],
                "mathematical_fraud_score": 0.0,
                "wolfram_responses": [],
            }

            # Check for impossible mathematical relationships
            fraud_analysis.update(self._detect_impossible_calculations(text))

            # Verify currency calculations if multiple currencies present
            fraud_analysis.update(self._verify_currency_calculations(text))

            # Check for unrealistic financial ratios
            amounts = extracted_fields.get("amounts", [])
            if amounts:
                fraud_analysis.update(self._detect_unrealistic_amounts(amounts))

            # Set fraud detection flags
            fraud_analysis["checks"]["wolfram_fraud_detection"] = True
            fraud_analysis["checks"]["mathematical_fraud_detected"] = (
                fraud_analysis["mathematical_fraud_score"] > 0.3
            )

            logger.info(
                f"Wolfram fraud detection completed with score: {fraud_analysis['mathematical_fraud_score']}"
            )

            return fraud_analysis

        except Exception as e:
            logger.error(f"Wolfram fraud detection failed: {str(e)}")
            return {
                "checks": {"wolfram_fraud_detection_failed": True},
                "indicators": [f"Wolfram fraud detection error: {str(e)}"],
                "mathematical_fraud_score": 0.0,
                "wolfram_responses": [],
            }

    def _detect_impossible_calculations(self, text: str) -> Dict[str, Any]:
        """Detect mathematically impossible calculations"""
        results = {
            "indicators": [],
            "mathematical_fraud_score": 0.0,
            "wolfram_responses": [],
        }

        try:
            # Look for obvious mathematical impossibilities
            impossible_patterns = [
                r"(\d+(?:[.,]\d+)?)\s*[-+]\s*(\d+(?:[.,]\d+)?)\s*=\s*(\d+(?:[.,]\d+)?)",
                r"(\d+(?:[.,]\d+)?)\s*[×*]\s*(\d+(?:[.,]\d+)?)\s*=\s*(\d+(?:[.,]\d+)?)",
                r"(\d+(?:[.,]\d+)?)\s*[÷/]\s*(\d+(?:[.,]\d+)?)\s*=\s*(\d+(?:[.,]\d+)?)",
            ]

            for pattern in impossible_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        # Convert to float for calculation
                        operand1 = float(match[0].replace(",", "."))
                        operand2 = float(match[1].replace(",", "."))
                        claimed_result = float(match[2].replace(",", "."))

                        # Determine operation and verify with Wolfram
                        if "+" in text[text.find(match[0]) : text.find(match[2])]:
                            query = f"What is {operand1} + {operand2}?"
                            operation = "addition"
                        elif "-" in text[text.find(match[0]) : text.find(match[2])]:
                            query = f"What is {operand1} - {operand2}?"
                            operation = "subtraction"
                        elif any(
                            op in text[text.find(match[0]) : text.find(match[2])]
                            for op in ["×", "*"]
                        ):
                            query = f"What is {operand1} * {operand2}?"
                            operation = "multiplication"
                        else:
                            query = f"What is {operand1} / {operand2}?"
                            operation = "division"

                        wolfram_response = wolfram_alpha_query(query)
                        results["wolfram_responses"].append(
                            {"query": query, "response": wolfram_response}
                        )

                        # Extract correct result from Wolfram
                        correct_result = self._extract_number_from_wolfram_response(
                            wolfram_response
                        )

                        if (
                            correct_result
                            and abs(correct_result - claimed_result) > 0.01
                        ):
                            results["indicators"].append(
                                f"Mathematical error in {operation}: {operand1} {'+' if operation == 'addition' else '-' if operation == 'subtraction' else '*' if operation == 'multiplication' else '/'} {operand2} = {claimed_result}, should be {correct_result}"
                            )
                            results[
                                "mathematical_fraud_score"
                            ] += 0.4  # High penalty for calculation errors

                    except ValueError:
                        continue

            return results

        except Exception as e:
            logger.warning(f"Impossible calculation detection failed: {str(e)}")
            return results

    def _verify_currency_calculations(self, text: str) -> Dict[str, Any]:
        """Verify currency exchange calculations"""
        results = {
            "indicators": [],
            "mathematical_fraud_score": 0.0,
            "wolfram_responses": [],
        }

        try:
            # Look for currency conversion patterns
            currency_patterns = [
                r"(\d+(?:[.,]\d+)?)\s*(USD|EUR|GBP)\s*=\s*(\d+(?:[.,]\d+)?)\s*(TL|₺)",
                r"(\d+(?:[.,]\d+)?)\s*(TL|₺)\s*=\s*(\d+(?:[.,]\d+)?)\s*(USD|EUR|GBP)",
            ]

            for pattern in currency_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        amount1 = float(match[0].replace(",", "."))
                        currency1 = match[1].upper()
                        amount2 = float(match[2].replace(",", "."))
                        currency2 = match[3].upper().replace("₺", "TL")

                        # Query current exchange rate from Wolfram
                        query = f"How much is {amount1} {currency1} in {currency2}?"
                        wolfram_response = wolfram_alpha_query(query)
                        results["wolfram_responses"].append(
                            {"query": query, "response": wolfram_response}
                        )

                        # Extract the conversion result
                        converted_amount = self._extract_number_from_wolfram_response(
                            wolfram_response
                        )

                        if converted_amount:
                            # Allow for reasonable tolerance (exchange rates fluctuate)
                            tolerance = converted_amount * 0.1  # 10% tolerance
                            if abs(converted_amount - amount2) > tolerance:
                                results["indicators"].append(
                                    f"Suspicious currency conversion: {amount1} {currency1} claimed as {amount2} {currency2}, current rate suggests ~{converted_amount:.2f} {currency2}"
                                )
                                results["mathematical_fraud_score"] += 0.3

                    except ValueError:
                        continue

            return results

        except Exception as e:
            logger.warning(f"Currency calculation verification failed: {str(e)}")
            return results

    def _detect_unrealistic_amounts(self, amounts: List[str]) -> Dict[str, Any]:
        """Detect unrealistic financial amounts using Wolfram Alpha"""
        results = {
            "indicators": [],
            "mathematical_fraud_score": 0.0,
            "wolfram_responses": [],
        }

        try:
            numeric_amounts = []
            for amount in amounts:
                # Extract numeric value
                cleaned = re.sub(r"[^\d.,]", "", str(amount))
                if cleaned:
                    if "," in cleaned:
                        cleaned = cleaned.replace(".", "").replace(",", ".")
                    try:
                        numeric_amounts.append(float(cleaned))
                    except ValueError:
                        continue

            for amount in numeric_amounts:
                # Check for unrealistically large amounts
                if amount > 1000000:  # Over 1 million TL
                    query = f"Is {amount} Turkish Lira a reasonable amount for a typical business transaction?"
                    wolfram_response = wolfram_alpha_query(query)
                    results["wolfram_responses"].append(
                        {"query": query, "response": wolfram_response}
                    )

                    # Simple check for unrealistic amounts
                    if amount > 10000000:  # Over 10 million TL
                        results["indicators"].append(
                            f"Extremely large amount detected: {amount} TL"
                        )
                        results["mathematical_fraud_score"] += 0.2

                # Check for unrealistically precise amounts (might be fabricated)
                if amount > 1000 and str(amount).endswith(".00"):
                    # Many round numbers might be suspicious
                    continue  # This is actually normal for invoices

            return results

        except Exception as e:
            logger.warning(f"Unrealistic amount detection failed: {str(e)}")
            return results

    def _extract_number_from_wolfram_response(self, response: str) -> Optional[float]:
        """Extract numerical result from Wolfram Alpha response"""
        try:
            # Look for numerical patterns in the response
            number_patterns = [
                r"(\d+(?:\.\d+)?)",
                r"(\d+(?:,\d+)*(?:\.\d+)?)",
            ]

            for pattern in number_patterns:
                matches = re.findall(pattern, response)
                if matches:
                    # Take the first number found
                    try:
                        return float(matches[0].replace(",", ""))
                    except ValueError:
                        continue

            return None

        except Exception:
            return None


# Verification pipeline instance
verification_pipeline = DocumentVerificationPipeline()
