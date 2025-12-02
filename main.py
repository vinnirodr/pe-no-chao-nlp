from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import re

app = FastAPI(
    title="Pé no Chão NLP API",
    description="Serviço de NLP para extrair premissas e conclusão de textos.",
    version="1.0.0",
)

class AnalyzeRequest(BaseModel):
    text: str

class Premise(BaseModel):
    text: str

class Conclusion(BaseModel):
    text: str

class AnalyzeResponse(BaseModel):
    premises: List[Premise]
    conclusion: Conclusion
    logical_structure: Optional[str] = None
    factual: Optional[str] = "inconclusivo"


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"[.!?]\s+", text.strip())
    sentences = [s.strip() for s in parts if s.strip()]
    return sentences

def extract_premises_and_conclusion(text: str):
    sentences = split_sentences(text)

    if len(sentences) == 1:
        premises = [sentences[0]]
        conclusion = "Conclusão não identificada explicitamente."
    else:
        premises = sentences[:-1]
        conclusion = sentences[-1]

    return premises, conclusion


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(payload: AnalyzeRequest):
    text = payload.text.strip()

    if len(text) < 10:
        premises = [text]
        conclusion = "Texto muito curto para análise robusta."
    else:
        premises, conclusion = extract_premises_and_conclusion(text)

    premises_objs = [Premise(text=p) for p in premises]
    conclusion_obj = Conclusion(text=conclusion)

    logical_structure = f"{len(premises_objs)} premissas → 1 conclusão"
    factual = "inconclusivo"

    return AnalyzeResponse(
        premises=premises_objs,
        conclusion=conclusion_obj,
        logical_structure=logical_structure,
        factual=factual,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "nlp-api", "version": "1.0.0"}
