import os, json, textwrap
from pathlib import Path
from typing import Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Configs de segurança de tokens (alvo ~4k):
MAX_PROFILE_CHARS = 12000  # compacta o JSON do profile
MAX_MEMORY_CHARS  = 6000   # compacta a memória passada ao LLM
MAX_ANSWER_CHARS  = 6000   # limite de resposta (pós LLM)

def _compact_json(d: Dict[str, Any], max_chars: int) -> str:
    """Compacta JSON priorizando chaves mais úteis; corta se exceder."""
    # prioridade de chaves mais relevantes do profile/memória
    priority = ["filename", "rows_total", "fraud_rate", "class_counts", "columns",
                "numeric_stats", "summary", "findings", "history"]
    copy = {}
    for k in priority:
        if k in d:
            copy[k] = d[k]
    s = json.dumps(copy, separators=(",", ":"), ensure_ascii=False)
    if len(s) > max_chars:
        s = s[:max_chars] + "...[truncated]"
    return s

SYSTEM_INSTRUCTIONS = textwrap.dedent("""
Você é um agente de EDA. Responda de forma objetiva, com números e nomes de colunas.
- NUNCA invente colunas que não existem.
- Se precisar de gráfico, descreva qual gráfico gerar (ex.: 'histogram Amount bins=50 log'), que o executor fará.
- Baseie-se no PROFILE (resumo global) e na MEMORY (insights prévios).
- Se a pergunta não for clara, peça refinamento em UMA frase curta.
- Prefira bullets e tabelas curtas.
- Mantenha a resposta até ~300 palavras quando possível.
""").strip()

def _build_prompt(question: str, profile: Dict[str, Any], memory: Dict[str, Any]) -> str:
    profile_j = _compact_json(profile, MAX_PROFILE_CHARS)
    memory_j  = _compact_json(memory or {}, MAX_MEMORY_CHARS)
    return f"""SYSTEM:\n{SYSTEM_INSTRUCTIONS}\n\nPROFILE(JSON):\n{profile_j}\n\nMEMORY(JSON):\n{memory_j}\n\nUSER QUESTION:\n{question}\n\nASSISTANT:"""

# -------- Providers --------
def _call_gemini(prompt: str) -> str:
    import google.generativeai as genai
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return "⚠️ GEMINI_API_KEY não configurada."
    genai.configure(api_key=key)
    # modelo default
    model = genai.GenerativeModel("gemini-2.5-flash")
    resp = model.generate_content(prompt)
    text = getattr(resp, "text", "") or (resp.candidates[0].content.parts[0].text if resp.candidates else "")
    return text[:MAX_ANSWER_CHARS] or "⚠️ Resposta vazia do Gemini."

def _call_openai(prompt: str) -> str:
    from openai import OpenAI
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return "⚠️ OPENAI_API_KEY não configurada."
    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=800
    )
    text = resp.choices[0].message.content or ""
    return text[:MAX_ANSWER_CHARS] or "⚠️ Resposta vazia do OpenAI."

def llm_respond(question: str, profile: Dict[str, Any], memory: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Retorna (answer_text, meta). Meta pode conter flags como 'needs_plot' ou instruções de execução.
    """
    prompt = _build_prompt(question, profile, memory)
    if LLM_PROVIDER == "gpt":
        answer = _call_openai(prompt)
    else:
        answer = _call_gemini(prompt)

    # Extração simples de comandos de gráfico do texto (protocolo leve)
    meta = {}
    lower = answer.lower()
    if "histogram" in lower and "amount" in lower:
        meta["plot"] = {"type": "hist_amount", "column": "Amount", "bins": 50, "log": True}
    if "time series" in lower or "série temporal" in lower:
        meta.setdefault("plot", {"type": "timeseries", "column": "Time"})

    return answer, meta