from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Literal

try:
    from backend.shared.logger import get_logger
    from backend.pipeline.upload import parse_document
    from agents import Agent, Runner, AgentOutputSchema
except ImportError:
    # For direct execution, use relative imports
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from backend.shared.logger import get_logger
    from backend.pipeline.upload import parse_document
    from agents import Agent, Runner, AgentOutputSchema
from pydantic import BaseModel, Field

logger = get_logger("DOCUMENT_VERIFICATION")


class DocumentType(BaseModel):
    detected_type: Literal[
        "invoice",
        "receipt",
        "bank_statement",
        "payslip",
        "contract",
        "tax_declaration",
        "expense_voucher",
        "other",
    ]
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score between 0 and 1"
    )
    reasoning: str = Field(description="Explanation of classification")
    key_indicators: List[str] = Field(description="List of key terms found")


class QualityAssessment(BaseModel):
    overall_quality: Literal["high", "medium", "low"]
    quality_score: float = Field(
        ge=0.0, le=1.0, description="Quality score between 0 and 1"
    )
    issues: List[str] = Field(description="List of quality issues")
    strengths: List[str] = Field(description="List of quality strengths")


class ExtractedFields(BaseModel):
    dates: List[str] = Field(
        default_factory=list, description="All dates found in document"
    )
    amounts: List[str] = Field(default_factory=list, description="All monetary amounts")
    tax_numbers: List[str] = Field(
        default_factory=list, description="Turkish tax numbers (10 digits)"
    )
    ibans: List[str] = Field(default_factory=list, description="Turkish IBAN numbers")
    company_names: List[str] = Field(
        default_factory=list, description="Company or business names"
    )
    document_numbers: List[str] = Field(
        default_factory=list, description="Invoice numbers, receipt numbers, etc."
    )
    currencies: List[str] = Field(
        default_factory=list, description="Currencies mentioned"
    )
    parties: Dict[str, str] = Field(
        default_factory=dict, description="Seller and buyer information"
    )


class ValidationResults(BaseModel):
    is_valid: bool = Field(description="Whether the document is valid")
    validation_score: float = Field(
        ge=0.0, le=1.0, description="Validation score between 0 and 1"
    )
    missing_fields: List[str] = Field(
        default_factory=list, description="List of missing required fields"
    )
    format_issues: List[str] = Field(
        default_factory=list, description="List of format problems"
    )
    calculation_errors: List[str] = Field(
        default_factory=list, description="List of mathematical errors"
    )
    date_issues: List[str] = Field(
        default_factory=list, description="List of date-related problems"
    )


class FraudAnalysis(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    risk_score: float = Field(ge=0.0, le=1.0, description="Risk score between 0 and 1")
    fraud_indicators: List[str] = Field(
        default_factory=list, description="List of fraud indicators"
    )
    suspicious_patterns: List[str] = Field(
        default_factory=list, description="List of suspicious patterns"
    )
    unrealistic_elements: List[str] = Field(
        default_factory=list, description="List of unrealistic elements"
    )
    overall_assessment: str = Field(description="Overall fraud risk assessment")


class DataConsistency(BaseModel):
    is_consistent: bool = Field(description="Whether data is consistent")
    consistency_score: float = Field(
        ge=0.0, le=1.0, description="Consistency score between 0 and 1"
    )
    date_consistency: Literal["consistent", "inconsistent"]
    calculation_accuracy: Literal["accurate", "inaccurate"]
    cross_field_validation: Literal["valid", "invalid"]
    business_logic_compliance: Literal["compliant", "non-compliant"]


class Recommendations(BaseModel):
    action_required: Literal["none", "review", "reject"]
    priority: Literal["low", "medium", "high"]
    suggestions: List[str] = Field(
        default_factory=list, description="List of improvement suggestions"
    )
    manual_review_needed: bool = Field(description="Whether manual review is needed")


class ConfidenceSummary(BaseModel):
    overall_confidence: float = Field(
        ge=0.0, le=1.0, description="Overall confidence score between 0 and 1"
    )
    verification_status: Literal["verified", "review_required", "rejected"]
    reliability_factors: List[str] = Field(
        description="List of factors affecting confidence"
    )


class VerificationResult(BaseModel):
    document_type: DocumentType
    quality_assessment: QualityAssessment
    extracted_fields: ExtractedFields
    validation_results: ValidationResults
    fraud_analysis: FraudAnalysis
    data_consistency: DataConsistency
    recommendations: Recommendations
    confidence_summary: ConfidenceSummary


verification_agent = Agent(
    name="Document Verification Agent",
    instructions="""You are an expert document verification analyst specializing in Turkish financial documents. 
            Your task is to analyze documents thoroughly and provide accurate, structured verification results.
            
            CRITICAL: You must return a JSON object with ALL these top-level fields:
            - document_type: Classification and confidence
            - quality_assessment: Overall quality and issues
            - extracted_fields: All data extracted from document
            - validation_results: Validation checks and results
            - fraud_analysis: Risk assessment
            - data_consistency: Consistency checks
            - recommendations: Action recommendations
            - confidence_summary: Overall confidence
            
            Make sure each field is properly structured and all required sub-fields are included.
            
            Analyze the document for:
            1. Document type classification (invoice, receipt, etc.)
            2. Quality assessment (high/medium/low with score)
            3. Field extraction (dates, amounts, tax numbers, etc.)
            4. Validation checks (format, calculations, etc.)
            5. Fraud risk analysis (low/medium/high risk)
            6. Data consistency (consistent/inconsistent)
            7. Recommendations (none/review/reject)
            8. Overall confidence summary (verified/review_required/rejected)
            
            Always provide detailed reasoning and evidence for your conclusions.""",
    output_type=AgentOutputSchema(VerificationResult, strict_json_schema=False),
)


async def verify_document(file_path: str) -> Dict[str, Any]:
    """
    Main verification function that uses OpenAI Agents SDK
    """
    try:
        logger.info(f"Starting verification for: {file_path}")

        parsed_text = await parse_document(file_path)

        if not parsed_text or len(parsed_text.strip()) < 10:
            logger.warning(f"Insufficient text extracted from {file_path}")
            return {
                "error": "Insufficient text extracted",
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
            }

        verification_result = await Runner.run(verification_agent, parsed_text)

        # Extract the actual VerificationResult from RunResult
        if hasattr(verification_result, "final_output"):
            # OpenAI Agents SDK returns a RunResult with final_output
            actual_result = verification_result.final_output
        else:
            actual_result = verification_result

        # Convert to dict
        if hasattr(actual_result, "model_dump"):
            result_data = actual_result.model_dump()
        elif hasattr(actual_result, "dict"):
            result_data = actual_result.dict()
        elif hasattr(actual_result, "__dict__"):
            result_data = actual_result.__dict__
        else:
            result_data = str(actual_result)

        # Format result for frontend compatibility
        result = {
            "file_name": Path(file_path).name,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "parsed_text_length": len(parsed_text),
            # Main fields expected by frontend
            "verification_type": result_data.get("document_type", {}).get(
                "detected_type", "unknown"
            ),
            "confidence_score": result_data.get("confidence_summary", {}).get(
                "overall_confidence", 0
            ),
            "verification_status": result_data.get("confidence_summary", {}).get(
                "verification_status", "unknown"
            ),
            # Stages for frontend display
            "stages": {
                "quality_control": {
                    "passed": result_data.get("quality_assessment", {}).get(
                        "overall_quality"
                    )
                    in ["high", "medium"],
                    "score": result_data.get("quality_assessment", {}).get(
                        "quality_score", 0
                    ),
                    "issues": result_data.get("quality_assessment", {}).get(
                        "issues", []
                    ),
                    "assessment": f"Quality: {result_data.get('quality_assessment', {}).get('overall_quality', 'unknown')}",
                },
                "classification": {
                    "passed": result_data.get("document_type", {}).get("confidence", 0)
                    >= 0.7,
                    "score": result_data.get("document_type", {}).get("confidence", 0),
                    "reasoning": result_data.get("document_type", {}).get(
                        "reasoning", ""
                    ),
                    "assessment": f"Detected as: {result_data.get('document_type', {}).get('detected_type', 'unknown')}",
                },
                "data_consistency": {
                    "consistent": result_data.get("data_consistency", {}).get(
                        "is_consistent", False
                    ),
                    "score": result_data.get("data_consistency", {}).get(
                        "consistency_score", 0
                    ),
                    "assessment": f"Data consistency: {result_data.get('data_consistency', {}).get('date_consistency', 'unknown')}",
                },
                "fraud_analysis": {
                    "risk_level": result_data.get("fraud_analysis", {}).get(
                        "risk_level", "unknown"
                    ),
                    "score": 1.0
                    - result_data.get("fraud_analysis", {}).get(
                        "risk_score", 0
                    ),  # Invert for display (higher is better)
                    "assessment": result_data.get("fraud_analysis", {}).get(
                        "overall_assessment", ""
                    ),
                    "indicators": result_data.get("fraud_analysis", {}).get(
                        "fraud_indicators", []
                    ),
                },
                "template_validation": {
                    "valid": result_data.get("validation_results", {}).get(
                        "is_valid", False
                    ),
                    "score": result_data.get("validation_results", {}).get(
                        "validation_score", 0
                    ),
                    "issues": result_data.get("validation_results", {}).get(
                        "format_issues", []
                    ),
                    "assessment": (
                        "Valid"
                        if result_data.get("validation_results", {}).get(
                            "is_valid", False
                        )
                        else "Invalid"
                    ),
                },
            },
            # Warnings and errors
            "warnings": result_data.get("quality_assessment", {}).get("issues", [])
            + result_data.get("validation_results", {}).get("missing_fields", []),
            "errors": result_data.get("validation_results", {}).get(
                "calculation_errors", []
            )
            + result_data.get("validation_results", {}).get("date_issues", []),
            # Raw verification result for debugging
            "verification_result": result_data,
        }

        logger.info(f"Verification completed for: {file_path}")
        return result

    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        return {
            "error": str(e),
            "status": "failed",
            "timestamp": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    import asyncio

    print(
        asyncio.run(
            verify_document(
                "C:/Users/ASUS/Desktop/Coding/CanProjects/AIris/backend/database/verification_uploads/Invoice-3235832400.pdf"
            )
        )
    )
