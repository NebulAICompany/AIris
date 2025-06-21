# Test Documents for AIRIS Document Verification

This folder contains test documents designed to test the document verification system with both problematic and clean documents.

## 📋 Test Documents

### 🔴 **suspicious_invoice.pdf** (Problematic Document)

**Expected Result:** Should **FAIL** verification with multiple warnings and errors.

**Red Flags Included:**
- **Invalid Date:** Vade Tarihi: 32.13.2024 (impossible date)
- **Date Inconsistency:** Fatura dated after düzenleme date
- **Suspicious Amount:** 999,999,999.99 TL (unrealistically high)
- **Incorrect Calculation:** KDV calculation doesn't match the amounts
- **Invalid IBAN:** TR00 0000 0000 0000 0000 0000 00
- **Suspicious Bank Name:** "Photoshop Bank"
- **Fraud Indicators:** 
  - Contains text "photoshop ile düzenlenmiştir"
  - Contains "FAKE_INVOICE_GENERATOR"
  - Contains "kopya/duplicate" warning
- **Suspicious Terms:** 500% interest rate threat
- **Suspicious Person Name:** "Sahte İsim" (Fake Name)

**Verification Stages Expected Results:**
- ✅ Quality Control: PASS (file format OK)
- ✅ Classification: PASS (detected as invoice) 
- ✅ Text Extraction: PASS (text readable)
- ❌ Template Validation: FAIL (invalid dates, amounts)
- ❌ Data Consistency: FAIL (inconsistent dates, wrong calculations)
- ❌ Fraud Analysis: HIGH RISK (multiple red flags)

**Overall Status:** ❌ **REJECTED**

---

### 🟢 **clean_receipt.pdf** (Clean Document)

**Expected Result:** Should **PASS** verification with high confidence.

**Legitimate Features:**
- **Valid Company:** Migros (real Turkish retail chain)
- **Proper Tax Number:** Valid 10-digit format
- **Consistent Dates:** All dates are valid and consistent
- **Reasonable Amounts:** Normal grocery shopping amounts
- **Correct Calculations:** KDV calculations are accurate
- **Professional Format:** Standard retail receipt format
- **Complete Information:** All required fields present
- **No Suspicious Text:** No fraud indicators

**Verification Stages Expected Results:**
- ✅ Quality Control: PASS
- ✅ Classification: PASS (detected as receipt)
- ✅ Text Extraction: PASS 
- ✅ Template Validation: PASS
- ✅ Data Consistency: PASS
- ✅ Fraud Analysis: LOW RISK

**Overall Status:** ✅ **VERIFIED**

---

## 🧪 How to Test

1. **Start the AIRIS backend server**
2. **Open the AIRIS UI application**
3. **Navigate to "Document Verification" tab**
4. **Test the suspicious invoice:**
   - Upload `suspicious_invoice.pdf`
   - Set verification type to "Fatura" or "Auto-detect"
   - Click "Verify Document"
   - **Expected:** Multiple warnings, low confidence score, REJECTED status

5. **Test the clean receipt:**
   - Upload `clean_receipt.pdf` 
   - Set verification type to "Fiş/Makbuz" or "Auto-detect"
   - Click "Verify Document"
   - **Expected:** High confidence score, VERIFIED status

## 📊 Expected Verification Results Summary

| Document | Type | Status | Confidence | Risk Level | Key Issues |
|----------|------|--------|------------|------------|------------|
| suspicious_invoice.pdf | Invoice | ❌ REJECTED | <40% | HIGH | Invalid dates, suspicious amounts, fraud indicators |
| clean_receipt.pdf | Receipt | ✅ VERIFIED | >85% | LOW | None - legitimate document |

## 🔧 Troubleshooting

If documents don't verify as expected:
1. Check if OCR dependencies are installed (pytesseract, opencv-python)
2. Verify the backend server is running
3. Check browser console for any JavaScript errors
4. Review backend logs for processing errors

## 📝 Creating More Test Documents

To create additional test documents, you can:
1. Edit the `.txt` files in this directory
2. Run `python create_test_pdfs.py` to regenerate PDFs
3. Or create new `.txt` files and modify the script to include them 