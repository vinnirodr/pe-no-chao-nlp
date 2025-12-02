import os
import re
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

APP_VERSION = "1.2.0"

app = FastAPI(
    title="Pé no Chão NLP API",
    description="Serviço de NLP para extrair premissas (P, Q, R) e conclusão (C) de textos.",
    version=APP_VERSION,
)


def get_allowed_origins() -> List[str]:
    raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
    parsed = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

    if not parsed or "*" in parsed:
        return ["*"]

    return parsed


ALLOWED_ORIGINS = get_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str


class Premise(BaseModel):
    label: str  # P, Q, R...
    text: str


class Conclusion(BaseModel):
    label: str = "C"
    text: str


class AnalyzeResponse(BaseModel):
    premises: List[Premise]
    conclusion: Conclusion
    propositions: Dict[str, str]
    logical_structure: Optional[str] = None
    factual: Optional[str] = "inconclusivo"


def split_sentences(text: str) -> List[str]:
    """
    Separa o texto em sentenças usando pontuação, cuidando de quebras de linha.
    """
    normalized = " ".join(text.split())
    parts = re.split(r"[.!?]\s+", normalized.strip())
    sentences = [s.strip() for s in parts if s.strip()]
    return sentences


def extract_premises_and_conclusion(text: str):
    """
    Regra simples:
    - Se só tiver 1 frase: vira P e a conclusão é genérica
    - Senão: todas as frases, menos a última, são premissas
            e a última é a conclusão (C)
    """
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

    if not text:
        raise HTTPException(status_code=400, detail="O campo 'text' não pode estar vazio.")

    if len(text) < 10:
        # texto muito curto, tratamos como um único P
        premise_labels = ["P"]
        premises_texts = [text]
        conclusion_text = "Texto muito curto para análise robusta."
    else:
        premises_texts, conclusion_text = extract_premises_and_conclusion(text)
        # até 3 premissas com rótulos P, Q, R
        premise_labels = ["P", "Q", "R"]

    premises_objs: List[Premise] = []

    for idx, p_text in enumerate(premises_texts):
        label = premise_labels[idx] if idx < len(premise_labels) else f"P{idx+1}"
        premises_objs.append(Premise(label=label, text=p_text))

    conclusion_obj = Conclusion(text=conclusion_text)

    # monta mapa de proposições P, Q, R, C
    propositions: Dict[str, str] = {
        prem.label: prem.text for prem in premises_objs
    }
    propositions["C"] = conclusion_obj.text

    logical_structure = f"{len(premises_objs)} premissas (P, Q, R...) → 1 conclusão (C)"
    factual = "inconclusivo"  # ainda não estamos checando fato aqui

    return AnalyzeResponse(
        premises=premises_objs,
        conclusion=conclusion_obj,
        propositions=propositions,
        logical_structure=logical_structure,
        factual=factual,
    )


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "nlp-api",
        "version": APP_VERSION,
        "allowed_origins": ALLOWED_ORIGINS,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "nlp-api", "version": APP_VERSION}
