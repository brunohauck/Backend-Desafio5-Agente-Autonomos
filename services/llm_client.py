from __future__ import annotations

def llm_respond(question: str, profile: dict, memory: dict):
    """Versão local simples (sem API externa).
    Retorna (answer, meta) e sugere plot com base em palavras-chave.
    """
    q = (question or "").lower()
    meta = None

    if any(k in q for k in ["histograma", "distribui", "distribution"]):
        meta = {"plot": {"type": "hist_amount", "bins": 60, "log": True}}
    elif "correlação" in q or "correlacao" in q or "heatmap" in q:
        meta = {"plot": {"type": "corr_heatmap", "sample_rows": 50000}}
    elif "série temporal" in q or "serie temporal" in q or "time series" in q:
        meta = {"plot": {"type": "timeseries", "bins": 120}}
    elif "boxplot" in q and "class" in q:
        meta = {"plot": {"type": "box_amount_by_class", "max_per_class": 20000}}
    elif "scatter" in q or "dispersão" in q or "dispersao" in q:
        meta = {"plot": {"type": "scatter", "x": "V1", "y": "V2", "sample_rows": 50000}}

    fraud_rate = profile.get("fraud_rate")
    mean_amount = (profile.get("means") or {}).get("Amount")
    count = profile.get("count")
    cols = profile.get("columns")

    parts = []
    if mean_amount is not None:
        parts.append(f"Média de Amount ≈ {mean_amount:.2f}.")
    if fraud_rate is not None:
        parts.append(f"Taxa de fraude ≈ {100*fraud_rate:.4f}%.")
    if count:
        parts.append(f"Total de linhas: {count}.")
    if cols:
        parts.append(f"Colunas: {len(cols)} variáveis (PCA V1..V28, Time, Amount, Class).")

    if not parts:
        parts.append("Perfil não encontrado; gere o perfil global antes de perguntar.")

    if any(k in q for k in ["conclus", "insight", "recomenda"]):
        parts.append("Conclusão inicial: a distribuição de Amount é assimétrica; fraude é rara. "
                     "Use boxplot por classe, histograma de Amount (log) e heatmap de correlação.")

    answer = " ".join(parts)
    return answer, meta