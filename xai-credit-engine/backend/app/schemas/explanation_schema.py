"""
app/schemas/explanation_schema.py
──────────────────────────────────────────────────────────────────────────────
XAI açıklama API Pydantic şemaları.
"""

from pydantic import BaseModel, Field


class ExplanationResponse(BaseModel):
    """GET /explanation/{inference_id} çıktısı."""
    explanation_id:   str
    inference_id:     str
    decision:         str
    boolean_formula:  str
    dnf_formula:      str
    natural_language: str
    technical_log:    str
    language_code:    str
    generated_at:     str
