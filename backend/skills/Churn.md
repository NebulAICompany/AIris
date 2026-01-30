---
name: churn-analysis-knowledge
description: Use this skill for requests related to customer churn analysis, retention strategies, and interpreting insurance churn signals.
---

# Churn Analysis & Retention Knowledge

## Overview

Customer churn (attrition/lapse) refers to policyholders discontinuing their insurance coverage. Retaining customers is critical as acquisition costs are 5-10x higher than retention. This skill provides domain knowledge for analyzing churn drivers, identifying at-risk customers, and recommending retention strategies.

## Critical Data Features

When analyzing churn, look for these variables in the data:
- **Policy Age**: Early-term (<2 years) vs. Long-term (different drivers).
- **Premium Changes**: Significant rate increases (>10%) at renewal.
- **Claims History**: Recent claims, especially with dissatisfaction signals.
- **Engagement**: Drop in portal/app usage (digital signal).
- **Payment Behavior**: Late payments, method changes.
- **Competitiveness**: Price difference vs. market.

## Instructions

### 1. Identify the Goal

Determine if the user wants to:
- **Analyze current churn stats**: "What is my churn rate?"
- **Understand drivers**: "Why are people leaving?"
- **Identify at-risk customers**: "Who will leave next?"
- **Develop retention strategies**: "How do I keep them?"

### 2. Gather Information

Use available tools to collect necessary context.

**Internal Data (Policy & Customer Context)**
Use `search_local_documents` to find:
- Policy renewal reports
- Customer feedback/surveys
- Cancellation reason codes
- Retention campaign results

**External Data (Market Context)**
Use `web_search_tool` to find:
- "Insurance market pricing trends [Region] [Year]"
- "Competitor retention offers [Product Type]"
- "Economic indicators affecting insurance [Region]"

### 3. Analyze & Diagnose

**common Churn Scenarios:**

| Scenario | Signals | Recommended Action |
| :--- | :--- | :--- |
| **Price Shock** | Rate increase >10%, no claims, price-sensitive segment. | Proactive active outreach to explain value/re-shop. |
| **Service Failure** | Low CSAT after claim, remaining term <6 months. | Service recovery, apology, dedication support. |
| **Involuntary** | Late payments, declined credit card. | Payment plan options, downgrade coverage offer. |
| **Life Event** | Address change, marraige/divorce. | Cross-sell bundle or re-evaluate needs. |

### 4. Provide Recommendations

- **Diagnostic**: "Churn increased 5% in the <30 age group following the April rate hike."
- **Strategic**: "Implement a 'rate-explanation' outreach for customers facing >10% increases."
- **Tactical**: "Flag customers with 2+ late payments for 'payment assistance' emails."

## Key Terminology

- **Persistence**: % of policies remaining in force.
- **Voluntary Churn**: Customer chooses to leave.
- **Involuntary Churn**: Termination for non-payment/underwriting.
- **Win-Back**: Campaigns to re-acquire lost customers.
