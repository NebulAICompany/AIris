from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Literal
from backend.shared.logger import get_logger
from backend.pipeline.upload import parse_document
from backend.core.prompts import verification_agent_prompt
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain.agents.structured_output import ToolStrategy
from backend.shared.constants import OPENAI_MODEL
from pydantic import BaseModel, Field

logger = get_logger("DOCUMENT_VERIFICATION")


class DocumentType(BaseModel):
    detected_type: Literal[
        "fatura",
        "fiş",
        "banka_ekstresi",
        "bordro",
        "sözleşme",
        "vergi_beyannamesi",
        "harcama_fişi",
        "duyuru",
        "diğer",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    key_indicators: List[str]


class QualityAssessment(BaseModel):
    overall_quality: Literal["yüksek", "orta", "düşük"]
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
    parties: Dict[str, List[str]] = Field(default_factory=dict)


class ValidationResults(BaseModel):
    is_valid: bool
    validation_score: float = Field(ge=0.0, le=1.0)
    missing_fields: List[str] = Field(default_factory=list)
    format_issues: List[str] = Field(default_factory=list)
    calculation_errors: List[str] = Field(default_factory=list)
    date_issues: List[str] = Field(default_factory=list)


class FraudAnalysis(BaseModel):
    risk_level: Literal["düşük", "orta", "yüksek"]
    risk_score: float = Field(ge=0.0, le=1.0)
    fraud_indicators: List[str] = Field(default_factory=list)
    suspicious_patterns: List[str] = Field(default_factory=list)
    unrealistic_elements: List[str] = Field(default_factory=list)
    overall_assessment: str


class DataConsistency(BaseModel):
    is_consistent: bool
    consistency_score: float = Field(ge=0.0, le=1.0)
    date_consistency: Literal["tutarlı", "tutarsız"]
    calculation_accuracy: Literal["doğru", "hatalı"]
    cross_field_validation: Literal["geçerli", "geçersiz"]
    business_logic_compliance: Literal["uyumlu", "uyumsuz"]


class Recommendations(BaseModel):
    action_required: Literal["onay", "inceleme", "red"]
    priority: Literal["düşük", "orta", "yüksek"]
    suggestions: List[str] = Field(default_factory=list)
    manual_review_needed: bool


class ConfidenceSummary(BaseModel):
    overall_confidence: float = Field(ge=0.0, le=1.0)
    verification_status: Literal["doğrulandı", "inceleme_gerekli", "reddedildi"]
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


# Create Deep Agent for document verification with structured output
verification_agent = create_agent(
    model=OPENAI_MODEL,
    tools=[],
    system_prompt=verification_agent_prompt,
    response_format=ToolStrategy(VerificationResult),
)

logger.info("Document Verification Agent initialized successfully")


async def verify_document(file_path: str) -> dict:
    """
    Main verification function that uses Deep Agents with structured output
    """
    logger.info(f"Starting document verification: {Path(file_path).name}")

    try:
        parsed_text = await parse_document(file_path)

        if not parsed_text or len(parsed_text.strip()) < 10:
            logger.warning("Document parsing failed - insufficient text extracted")
            return {
                "error": "Yetersiz metin çıkarıldı",
                "status": "başarısız",
                "timestamp": datetime.now().isoformat(),
            }

        logger.info(f"Document parsed successfully - Text length: {len(parsed_text)}")

        logger.info("Running verification Deep Agent...")
        verification_result = await verification_agent.ainvoke(
            {"messages": [HumanMessage(content=parsed_text)]}
        )
        logger.info("Verification Deep Agent completed successfully")

        # Extract structured output (same pattern as main agent)
        if (
            not isinstance(verification_result, dict)
            or "structured_response" not in verification_result
        ):
            logger.error("No structured_response found in verification result")
            return {
                "error": "Yapılandırılmış yanıt alınamadı",
                "status": "başarısız",
                "timestamp": datetime.now().isoformat(),
            }

        structured_data = verification_result["structured_response"]
        result_data = structured_data.model_dump()
        logger.info(f"Result data extracted - Keys: {list(result_data.keys())}")

        if not result_data:
            logger.error("Result data is empty! This will cause all scores to be 0%")

        result = format_result_for_frontend(file_path, parsed_text, result_data)
        logger.info(
            f"Verification completed - Status: {result.get('verification_status', 'bilinmeyen')}, "
            f"Confidence: {result.get('confidence_score', 0)}"
        )

        return result

    except Exception as e:
        logger.error(f"Verification failed: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "status": "başarısız",
            "timestamp": datetime.now().isoformat(),
        }


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

    # Build stages with direct Turkish values
    stages = {
        "kalite kontrol": {
            "passed": quality.get("overall_quality", "düşük") in ["yüksek", "orta"],
            "score": quality.get("quality_score", 0),
            "issues": quality.get("issues", []),
            "assessment": f"Kalite: {quality.get('overall_quality', 'bilinmeyen')}",
        },
        "belge sınıflandırma": {
            "passed": doc_type.get("confidence", 0) >= 0.7,
            "score": doc_type.get("confidence", 0),
            "reasoning": doc_type.get("reasoning", ""),
            "assessment": f"Tespit edilen: {doc_type.get('detected_type', 'bilinmeyen')}",
        },
        "veri tutarlılığı": {
            "consistent": consistency.get("is_consistent", False),
            "score": consistency.get("consistency_score", 0),
            "assessment": f"Veri tutarlılığı: {consistency.get('date_consistency', 'bilinmeyen')}",
        },
        "sahtekarlık analizi": {
            "risk_level": fraud.get("risk_level", "bilinmeyen"),
            "score": 1.0 - fraud.get("risk_score", 0),
            "assessment": fraud.get("overall_assessment", ""),
            "indicators": fraud.get("fraud_indicators", []),
        },
        "şablon doğrulama": {
            "valid": validation.get("is_valid", False),
            "score": validation.get("validation_score", 0),
            "issues": validation.get("format_issues", []),
            "assessment": (
                "Geçerli" if validation.get("is_valid", False) else "Geçersiz"
            ),
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
        "status": "Tamamlandı",
        "parsed_text_length": len(parsed_text),
        "verification_type": doc_type.get("detected_type", "bilinmeyen"),
        "confidence_score": confidence.get("overall_confidence", 0),
        "verification_status": confidence.get("verification_status", "bilinmeyen"),
        "stages": stages,
        "warnings": warnings,
        "errors": errors,
        "verification_result": result_data,
    }
