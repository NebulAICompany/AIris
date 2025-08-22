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
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    key_indicators: List[str]


class QualityAssessment(BaseModel):
    overall_quality: Literal["high", "medium", "low"]
    quality_score: float = Field(ge=0.0, le=1.0)
    issues: List[str]
    strengths: List[str]


class ExtractedFields(BaseModel):
    dates: List[str] = Field(default_factory=list)
    amounts: List[str] = Field(default_factory=list)
    tax_numbers: List[str] = Field(default_factory=list)
    ibans: List[str] = Field(default_factory=list)
    company_names: List[str] = Field(default_factory=list)
    document_numbers: List[str] = Field(default_factory=list)
    currencies: List[str] = Field(default_factory=list)
    parties: Dict[str, str] = Field(default_factory=dict)


class ValidationResults(BaseModel):
    is_valid: bool
    validation_score: float = Field(ge=0.0, le=1.0)
    missing_fields: List[str] = Field(default_factory=list)
    format_issues: List[str] = Field(default_factory=list)
    calculation_errors: List[str] = Field(default_factory=list)
    date_issues: List[str] = Field(default_factory=list)


class FraudAnalysis(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    risk_score: float = Field(ge=0.0, le=1.0)
    fraud_indicators: List[str] = Field(default_factory=list)
    suspicious_patterns: List[str] = Field(default_factory=list)
    unrealistic_elements: List[str] = Field(default_factory=list)
    overall_assessment: str


class DataConsistency(BaseModel):
    is_consistent: bool
    consistency_score: float = Field(ge=0.0, le=1.0)
    date_consistency: Literal["consistent", "inconsistent"]
    calculation_accuracy: Literal["accurate", "inaccurate"]
    cross_field_validation: Literal["valid", "invalid"]
    business_logic_compliance: Literal["compliant", "non-compliant"]


class Recommendations(BaseModel):
    action_required: Literal["none", "review", "reject"]
    priority: Literal["low", "medium", "high"]
    suggestions: List[str] = Field(default_factory=list)
    manual_review_needed: bool


class ConfidenceSummary(BaseModel):
    overall_confidence: float = Field(ge=0.0, le=1.0)
    verification_status: Literal["verified", "review_required", "rejected"]
    reliability_factors: List[str]


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

logger.info("Document Verification Agent initialized successfully")
logger.info(f"Agent name: {verification_agent.name}")


async def verify_document(file_path: str) -> Dict[str, Any]:
    """
    Main verification function that uses OpenAI Agents SDK
    """
    logger.info(f"Starting document verification: {file_path}")

    try:
        # Step 1: Parse document
        parsed_text = await parse_document(file_path)

        if not parsed_text or len(parsed_text.strip()) < 10:
            logger.warning(f"Document parsing failed - insufficient text extracted")
            return {
                "error": "Insufficient text extracted",
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
            }

        logger.info(f"Document parsed successfully - Text length: {len(parsed_text)}")

        # Step 2: Run verification agent
        logger.info("Running verification agent...")
        verification_result = await Runner.run(verification_agent, parsed_text)
        logger.info("Verification agent completed successfully")

        # Step 3: Process results
        result_data = extract_result_data(verification_result)
        logger.info(f"Result data extracted - Keys: {list(result_data.keys())}")

        # Step 4: Format result for frontend
        result = format_result_for_frontend(file_path, parsed_text, result_data)

        logger.info(
            f"Verification completed - Status: {result.get('verification_status', 'unknown')}, Confidence: {result.get('confidence_score', 0)}"
        )

        return result

    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")

        return {
            "error": str(e),
            "status": "failed",
            "timestamp": datetime.now().isoformat(),
        }


def extract_result_data(verification_result: Any) -> Dict[str, Any]:
    """Extract result data using the most appropriate method"""

    # Get the actual result from RunResult if needed
    actual_result = getattr(verification_result, "final_output", verification_result)

    # Convert to dict using the most appropriate method
    if hasattr(actual_result, "model_dump"):
        return actual_result.model_dump()
    elif hasattr(actual_result, "dict"):
        return actual_result.dict()
    elif hasattr(actual_result, "__dict__"):
        return actual_result.__dict__
    else:
        return {"raw_result": str(actual_result)}


def format_result_for_frontend(
    file_path: str, parsed_text: str, result_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Format verification result for frontend compatibility"""

    # Extract data with safe defaults
    doc_type = result_data.get("document_type", {})
    quality = result_data.get("quality_assessment", {})
    validation = result_data.get("validation_results", {})
    fraud = result_data.get("fraud_analysis", {})
    consistency = result_data.get("data_consistency", {})
    confidence = result_data.get("confidence_summary", {})

    # Build stages
    stages = {
        "quality_control": {
            "passed": quality.get("overall_quality", "low") in ["high", "medium"],
            "score": quality.get("quality_score", 0),
            "issues": quality.get("issues", []),
            "assessment": f"Quality: {quality.get('overall_quality', 'unknown')}",
        },
        "classification": {
            "passed": doc_type.get("confidence", 0) >= 0.7,
            "score": doc_type.get("confidence", 0),
            "reasoning": doc_type.get("reasoning", ""),
            "assessment": f"Detected as: {doc_type.get('detected_type', 'unknown')}",
        },
        "data_consistency": {
            "consistent": consistency.get("is_consistent", False),
            "score": consistency.get("consistency_score", 0),
            "assessment": f"Data consistency: {consistency.get('date_consistency', 'unknown')}",
        },
        "fraud_analysis": {
            "risk_level": fraud.get("risk_level", "unknown"),
            "score": 1.0 - fraud.get("risk_score", 0),
            "assessment": fraud.get("overall_assessment", ""),
            "indicators": fraud.get("fraud_indicators", []),
        },
        "template_validation": {
            "valid": validation.get("is_valid", False),
            "score": validation.get("validation_score", 0),
            "issues": validation.get("format_issues", []),
            "assessment": "Valid" if validation.get("is_valid", False) else "Invalid",
        },
    }

    # Build warnings and errors
    warnings = quality.get("issues", []) + validation.get("missing_fields", [])
    errors = validation.get("calculation_errors", []) + validation.get(
        "date_issues", []
    )

    return {
        "file_name": Path(file_path).name,
        "timestamp": datetime.now().isoformat(),
        "status": "completed",
        "parsed_text_length": len(parsed_text),
        "verification_type": doc_type.get("detected_type", "unknown"),
        "confidence_score": confidence.get("overall_confidence", 0),
        "verification_status": confidence.get("verification_status", "unknown"),
        "stages": stages,
        "warnings": warnings,
        "errors": errors,
        "verification_result": result_data,
    }
