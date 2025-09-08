from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Literal
from backend.shared.logger import get_logger
from backend.pipeline.upload import parse_document
from agents import Agent, Runner, AgentOutputSchema
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
        "announcement",
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
    parties: Dict[str, List[str]] = Field(default_factory=dict)


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
    name="Belge Doğrulama Ajanı",
    instructions="""
Sen Türk muhasebe standartları, vergi mevzuatı ve iş uygulamaları konusunda derin bilgiye sahip uzman bir finansal belge doğrulama analistisin. 
Görevin; finansal belgeleri kapsamlı şekilde incelemek ve doğru, uygulanabilir doğrulama sonuçları üretmektir.

## KRİTİK ÇIKTI GEREKSİNİMLERİ
Aşağıdaki üst düzey alanların **tamamını** içeren bir JSON nesnesi döndür (herhangi bir alanın eksik olması hata sebebidir):
- document_type: Belge türü sınıflandırması ve güven analizi
- quality_assessment: Belgenin kalite değerlendirmesi
- extracted_fields: Belgede çıkarılan tüm yapılandırılmış veriler
- validation_results: Teknik doğrulama kontrolleri
- fraud_analysis: Risk değerlendirmesi ve şüpheli durum tespiti
- data_consistency: Alanlar arası tutarlılık ve iş mantığı kontrolü
- recommendations: Açık ve net eylem önerileri
- confidence_summary: Genel güvenilirlik değerlendirmesi

## DOĞRULAMA METODOLOJİSİ

### 1. BELGE TÜRÜ SINIFLANDIRMASI
Belgeleri şu kategorilere ayır:
- *fatura (invoice):* Vergi numarası, fatura numarası, vade tarihi, satır kalemleri içerir
- *fiş (receipt):* Basit işlem kaydı, genellikle KDV ayrıştırması yoktur
- *banka ekstresi (bank_statement):* Hesap hareketleri, bakiyeler, banka logosu
- *bordro (payslip):* Maaş detayları, vergi kesintileri, işveren bilgisi
- *sözleşme (contract):* Hukuki anlaşma, imzalar, şartlar
- *vergi beyannamesi (tax_declaration):* Resmî vergi formları, vergi dairesi kaşeleri
- *harcama fişi (expense_voucher):* İç harcama belgeleri
- *duyuru (announcement):* Kurum içi veya resmî finansal bilgilendirme belgeleri, yönetim duyuruları, KAP bildirileri, şirket içi finansal yazılar

*Sınıflandırma Güveni:*
- ≥0.9 = yüksek güven (birden fazla belirgin gösterge mevcut)
- 0.7–0.89 = orta güven (çoğu gösterge mevcut, küçük belirsizlikler)
- <0.7 = düşük güven (yetersiz veya çelişkili göstergeler)

### 2. KALİTE DEĞERLENDİRMESİ
Belge kalitesini şu faktörlere göre değerlendir:

- *Yüksek kalite (≥0.8):* Net, eksiksiz, artefakt yok
- *Orta kalite (0.5–0.79):* Genelde okunaklı, küçük sorunlar mevcut
- *Düşük kalite (<0.5):* Okunamaz, kritik alanlar eksik

### 3. ALAN ÇIKARIMI STANDARTLARI
Şu Türk finansal belge unsurlarını çıkar ve doğrula:

- *Tarihler:* (GG.AA.YYYY veya GG/AA/YYYY)
- *Tutarlar:* Türk Lirası (₺, TL) ve yabancı para birimleri (USD, EUR)
- *Vergi numarası (VKN):* 10 haneli olmalı
- *IBAN:* TR ile başlayan ve 24 haneli
- *Şirket bilgileri, fatura/fiş numaraları*
- *Satır kalemleri, ara toplamlar, KDV oranları (1%, 8%, 18%, 20%)*

### 4. DOĞRULAMA KONTROLLERİ
Zorunlu kontroller:

- Format doğrulama (tarih, vergi no, IBAN)
- Hesaplama doğrulama (KDV, toplamlar)
- Tarih mantığı doğrulama (düzenleme tarihi ≤ vade tarihi, gelecekte olmamalı)

### 5. SAHTECİLİK (FRAUD) ANALİZ GÖSTERGELERİ
Risk değerlendirmesi:

- *Yüksek risk:* Vergi bilgisi eksik, değiştirilmiş alanlar, kopya numaralar, şüpheli tutarlar
- *Orta risk:* Küçük format uyumsuzlukları, alışılmadık ama mümkün işlemler
- *Düşük risk:* Tutarlı, profesyonel, tüm yasal zorunluluklar mevcut, şirket bilgisi doğrulanabilir

### 6. VERİ TUTARLILIĞI KURALLARI
- Tarihler mantıklı olmalı
- Ara toplamlar satır kalemleriyle uyuşmalı
- Alanlar arası veriler birbiriyle desteklenmeli
- Matematiksel doğruluk sağlanmalı

### 7. ÖNERİ MATRİSİ
Sonuçlara göre önerilen aksiyon:

- *none (onayla):* Yüksek kalite + düşük risk + tutarlı
- *review (manuel inceleme):* Orta kalite/risk veya küçük hatalar
- *reject (reddet):* Düşük kalite, yüksek risk veya kritik doğrulama hataları, sahtecilik belirtileri

### 8. GÜVEN SKORLAMA
Genel güveni şu ağırlıklarla hesapla:

- Belge kalitesi: %25
- Alan çıkarımı tamlığı: %20
- Doğrulama başarısı: %25  
- Sahtecilik riski (ters orantılı): %20
- Veri tutarlılığı: %10

*Doğrulama Statüsü:*
- *verified:* ≥0.8 güven, yüksek risk yok
- *review_required:* 0.5–0.79 güven, bazı endişeler
- *rejected:* <0.5 güven, ciddi sorunlar

## CEVAP YÖNERGELERİ
- Sonuçlar için her zaman somut kanıt sun
- Türk iş ve finans terminolojisini kullan
- Sorunları sayı ve örneklerle belirt
- Önerilerde uygulanabilir adımlar sun
- Profesyonel, analitik ve net bir dil kullan

## ÖZEL DURUMLAR
- Okunamayan metinler: Manuel inceleme notu düş
- Yabancı belgeler: Yanlış sınıflandırma ihtimalini işaretle
- Hasarlı belgeler: Sadece kritik alanlara etkisini değerlendir
- Olağandışı formatlar: Görünüşe değil içeriğe göre değerlendir


## JSON ÇIKTI ÖRNEĞİ VE FORMAT
Çıktının kesinlikle aşağıdaki format ve alanları içermesi gerekir:
```json
{
  "document_type": {
    "detected_type": "fatura",
    "confidence": 0.85,
    "reasoning": "Açık açıklama",
    "key_indicators": ["gösterge1", "gösterge2"]
  },
  "quality_assessment": {
    "overall_quality": "high",
    "quality_score": 0.9,
    "issues": [],
    "strengths": ["güçlü yön1"]
  },
  "extracted_fields": {
    "dates": ["2024-01-01"],
    "amounts": ["1000.00"],
    "tax_numbers": ["1234567890"],
    "ibans": ["TR123456789012345678901234"],
    "company_names": ["Şirket Adı"],
    "document_numbers": ["FT2024001"],
    "currencies": ["TRY"],
    "parties": {
      "individuals": ["Kişi Adı"],
      "entities": ["Tüzel Kişi Adı"]
    }
  },
  "validation_results": {
    "is_valid": true,
    "validation_score": 0.85,
    "missing_fields": [],
    "format_issues": [],
    "calculation_errors": [],
    "date_issues": []
  },
  "fraud_analysis": {
    "risk_level": "low",
    "risk_score": 0.1,
    "fraud_indicators": [],
    "suspicious_patterns": [],
    "unrealistic_elements": [],
    "overall_assessment": "Güvenli belge"
  },
  "data_consistency": {
    "is_consistent": true,
    "consistency_score": 0.95,
    "date_consistency": "consistent",
    "calculation_accuracy": "accurate", 
    "cross_field_validation": "valid",
    "business_logic_compliance": "compliant"
  },
  "recommendations": {
    "action_required": "none",
    "priority": "low",
    "suggestions": ["öneri1"],
    "manual_review_needed": false
  },
  "confidence_summary": {
    "overall_confidence": 0.89,
    "verification_status": "verified",
    "reliability_factors": ["faktör1", "faktör2"]
  }
}
```

ÖNEMLİ NOTLAR:
- "parties" alanı mutlaka {"individuals": ["liste"], "entities": ["liste"]} formatında olmalı
- Tüm score alanları 0.0-1.0 arasında float olmalı  
- "verification_status" sadece "verified", "review_required", "rejected" değerlerinden biri olmalı
- JSON syntax'ını kontrol et, virgül ve tırnak işaretlerini doğru kullan
""",
    output_type=AgentOutputSchema(VerificationResult, strict_json_schema=False),
)

logger.info("Document Verification Agent initialized successfully")
logger.info(f"Agent name: {verification_agent.name}")


def translate_verification_status(status: str) -> str:
    """Verification status değerlerini Türkçeye çevirir"""
    status_translations = {
        "verified": "Doğrulandı",
        "review_required": "İnceleme Gerekli", 
        "rejected": "Reddedildi",
        "completed": "Tamamlandı",
        "failed": "Başarısız",
        "processing": "İşleniyor",
        "unknown": "Bilinmeyen",
        "low": "Düşük",
        "medium": "Orta", 
        "high": "Yüksek"
    }
    return status_translations.get(status, status)

def translate_stage_names(stages: dict) -> dict:
    """Stage isimlerini Türkçeye çevirir"""
    stage_translations = {
        "quality_control": "Kalite Kontrol",
        "classification": "Belge Sınıflandırma",
        "text_extraction": "Metin Çıkarma", 
        "template_validation": "Şablon Doğrulama",
        "data_consistency": "Veri Tutarlılığı",
        "fraud_analysis": "Sahtekarlık Analizi"
    }
    
    translated_stages = {}
    for stage_key, stage_data in stages.items():
        translated_key = stage_translations.get(stage_key, stage_key)
        translated_stages[translated_key] = stage_data
    
    return translated_stages


async def verify_document(file_path: str, document_type: str = "auto") -> dict:
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
        logger.info(f"Verification completed - Status: {result.get('verification_status', 'unknown')}, Confidence: {result.get('confidence_score', 0)}")

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
    doc_type = result_data.get("document_type", {"not detected"})
    quality = result_data.get("quality_assessment", {"not detected"})
    validation = result_data.get("validation_results", {"not detected"})
    fraud = result_data.get("fraud_analysis", {"not detected"})
    consistency = result_data.get("data_consistency", {"not detected"})
    confidence = result_data.get("confidence_summary", {"not detected"})

    # Build stages
    stages = {
        "quality_control": {
            "passed": quality.get("overall_quality", "low") in ["high", "medium"],
            "score": quality.get("quality_score", 0),
            "issues": quality.get("issues", []),
            "assessment": f"Kalite: {translate_verification_status(quality.get('overall_quality', 'unknown'))}",
        },
        "classification": {
            "passed": doc_type.get("confidence", 0) >= 0.7,
            "score": doc_type.get("confidence", 0),
            "reasoning": doc_type.get("reasoning", ""),
            "assessment": f"Tespit edilen: {doc_type.get('detected_type', 'bilinmeyen')}",
        },
        "data_consistency": {
            "consistent": consistency.get("is_consistent", False),
            "score": consistency.get("consistency_score", 0),
            "assessment": f"Veri tutarlılığı: {consistency.get('date_consistency', 'bilinmeyen')}",
        },
        "fraud_analysis": {
            "risk_level": translate_verification_status(fraud.get("risk_level", "unknown")),
            "score": 1.0 - fraud.get("risk_score", 0),
            "assessment": fraud.get("overall_assessment", ""),
            "indicators": fraud.get("fraud_indicators", []),
        },
        "template_validation": {
            "valid": validation.get("is_valid", False),
            "score": validation.get("validation_score", 0),
            "issues": validation.get("format_issues", []),
            "assessment": "Geçerli" if validation.get("is_valid", False) else "Geçersiz",
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
        "status": translate_verification_status("completed"),
        "parsed_text_length": len(parsed_text),
        "verification_type": doc_type.get("detected_type", "unknown"),
        "confidence_score": confidence.get("overall_confidence", 0),
        "verification_status": translate_verification_status(confidence.get("verification_status", "unknown")),
        "stages": translate_stage_names(stages),
        "warnings": warnings,
        "errors": errors,
        "verification_result": result_data,
    }
