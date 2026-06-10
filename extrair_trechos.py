#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrai trechos verbatim e estatísticas reais das sessões do Claude Code
do projeto Consignado, gerando dados_apresentacao.json para o gerador
da apresentação (gerar_apresentacao_claude.py).
"""
import json
import os
import re
import glob
from datetime import datetime

TRANSCRIPT_DIR = os.path.expanduser(
    "~/.claude/projects/-mnt-d-Projetos-Consignado")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "dados_apresentacao.json")

# ---------------------------------------------------------------- helpers

def texto_user(msg):
    """Texto de uma mensagem do usuário real (ignora tool_results/lembretes)."""
    c = msg.get("message", {}).get("content")
    if isinstance(c, str):
        t = c
    elif isinstance(c, list):
        partes = [b.get("text", "") for b in c
                  if isinstance(b, dict) and b.get("type") == "text"]
        t = "\n".join(p for p in partes if p)
    else:
        return None
    t = t.strip()
    if not t or t.startswith("<") or "system-reminder" in t[:80]:
        return None
    return t


def blocos_assistant(msg):
    """(textos, tools) de uma mensagem do assistente."""
    c = msg.get("message", {}).get("content")
    textos, tools = [], []
    if isinstance(c, list):
        for b in c:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text" and b.get("text", "").strip():
                textos.append(b["text"].strip())
            elif b.get("type") == "tool_use":
                tools.append(b)
    elif isinstance(c, str) and c.strip():
        textos.append(c.strip())
    return textos, tools


def resumo_tool(tb):
    """Resumo legível de um tool_use (para o bloco estilo terminal)."""
    nome = tb.get("name", "?")
    inp = tb.get("input", {}) or {}
    if nome == "Bash":
        cmd = (inp.get("command") or "").strip()
        if cmd:
            return ("Bash", cmd)
    elif nome in ("Write", "Edit", "NotebookEdit"):
        fp = inp.get("file_path") or inp.get("notebook_path") or ""
        if fp:
            return (nome, fp)
    elif nome == "Read":
        return ("Read", inp.get("file_path", ""))
    return None


def iter_linhas(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue

# ---------------------------------------------------------------- momentos

# (id, arquivo-prefixo, regex âncora no prompt do usuário, título, valor)
MOMENTOS = [
    ("planejamento", "d4ee46fe",
     r"planejamento completo de um projeto",
     "Planejar antes de codar",
     "O Claude recebeu o pedido de um projeto inteiro do zero e, antes de "
     "escrever qualquer código, fechou o escopo com perguntas que mudavam a "
     "arquitetura — evitando retrabalho."),
    ("pgfn", "459f9a5f",
     r"pgfn.*devedora|devedora.*pgfn",
     "Pesquisa autônoma de dados públicos (PGFN)",
     "Uma pergunta aberta virou um mapa completo das fontes públicas da "
     "PGFN: categorias, campos, limitações e caminhos de acesso."),
    ("categoricas", "f5c3c13c",
     r"mesmo significado ao longo dos anos",
     "Bug silencioso evitado (RAIS entre anos)",
     "O Claude alertou que códigos categóricos da RAIS mudam de significado "
     "entre anos e validou isso nos dados reais — um erro que passaria "
     "despercebido no modelo."),
    ("gpu", "4125d06f",
     r"1000 itera",
     "Calibração de modelo em GPU remota (B200)",
     "Tuning sistemático de learning_rate × depth em GPU na nuvem, com "
     "algoritmo de calibração explícito até o early stopping ~1000 "
     "iterações."),
    ("ftp", "f261c368",
     r"ftp\.mtps\.gov\.br",
     "Dados públicos direto da fonte",
     "Verificação da atualização dos microdados da RAIS no FTP oficial e "
     "orquestração do download/processamento em background."),
    ("html_interativo", "f261c368",
     r"selecionar dinamicamente|dinamicamente quais",
     "A apresentação interativa gerada por conversa",
     "Um pedido em uma frase virou um HTML autossuficiente com curvas de "
     "sobrevivência selecionáveis por categoria — a apresentação usada com "
     "a diretoria."),
    ("tempo_medio", "f261c368",
     r"tempo m[ée]dio esperado|tempo.*at[ée] o desligamento",
     "Raciocínio conceitual, não só código",
     "Antes de calcular, o Claude separou o que o modelo realmente prevê do "
     "que foi perguntado, e propôs as abordagens corretas (Kaplan-Meier, "
     "Weibull)."),
]

SESSOES_INFO = {
    "eb9eac8b": "Análise exploratória (taxa_sjc, perfis de risco)",
    "4861c106": "Dados raw RAIS 2023 (CSV → Parquet)",
    "459f9a5f": "PGFN: devedores previdenciários/FGTS",
    "f5c3c13c": "Validação de categóricas entre anos",
    "d4ee46fe": "Sessão principal: planejamento e construção",
    "4125d06f": "Treino do ensemble em GPU B200",
    "78a33eaa": "Revisão de mudanças pendentes",
    "f261c368": "Sessão final: atualização, análises e apresentações",
}

# ------------------------------------------------------------- extração

def processa_sessao(path):
    sid = os.path.basename(path)[:8]
    stats = {"id": sid, "arquivo": os.path.basename(path),
             "descricao": SESSOES_INFO.get(sid, ""),
             "msgs_user": 0, "msgs_assistant": 0, "bash": 0,
             "arquivos_escritos": 0, "inicio": None, "fim": None,
             "primeiro_prompt": None, "pedidos": []}
    prompts = []  # (ordem, texto) de todos os pedidos do usuário
    eventos = []  # achatado: ("user", texto) / ("atext", t) / ("tool", resumo)
    for d in iter_linhas(path):
        ts = d.get("timestamp")
        if ts:
            if stats["inicio"] is None:
                stats["inicio"] = ts
            stats["fim"] = ts
        t = d.get("type")
        if t == "user":
            tx = texto_user(d)
            if tx:
                stats["msgs_user"] += 1
                if stats["primeiro_prompt"] is None:
                    stats["primeiro_prompt"] = tx[:600]
                prompts.append((len(prompts), tx))
                eventos.append(("user", tx))
        elif t == "assistant":
            stats["msgs_assistant"] += 1
            textos, tools = blocos_assistant(d)
            for tx in textos:
                eventos.append(("atext", tx))
            for tb in tools:
                r = resumo_tool(tb)
                nome = tb.get("name")
                if nome == "Bash":
                    stats["bash"] += 1
                elif nome in ("Write", "Edit", "NotebookEdit"):
                    stats["arquivos_escritos"] += 1
                if r:
                    eventos.append(("tool", r))
    # 5 principais pedidos: descarta ruído (respostas curtas tipo "sim",
    # "continue"), prioriza os mais substanciais e reordena cronologicamente
    RUIDO = re.compile(
        r"^(sim|n[aã]o|ok|continue|prossiga|pode|isso|exato|beleza|"
        r"perfeito|segue|vai|faça isso|aprovado)\b", re.IGNORECASE)
    cand = [(i, t) for i, t in prompts
            if i > 0  # o 1º pedido já é exibido à parte no painel
            and len(t) >= 40 and not RUIDO.match(t.strip())
            and not t.startswith("This session is being continued")
            and "ran out of context" not in t[:200]]
    top = sorted(cand, key=lambda x: len(x[1]), reverse=True)[:5]
    top.sort(key=lambda x: x[0])  # ordem cronológica
    stats["pedidos"] = [t[:220] + (" …" if len(t) > 220 else "")
                        for _, t in top]
    return stats, eventos


def acha_momento(eventos, padrao):
    """Acha o prompt do usuário que casa com o padrão e coleta a resposta."""
    rx = re.compile(padrao, re.IGNORECASE | re.DOTALL)
    for i, (tipo, payload) in enumerate(eventos):
        if tipo != "user" or not rx.search(payload):
            continue
        prompt = payload
        resposta, tools = [], []
        for tipo2, p2 in eventos[i + 1:]:
            if tipo2 == "user":
                break
            if tipo2 == "atext":
                resposta.append(p2)
            elif tipo2 == "tool" and len(tools) < 4:
                tools.append({"tool": p2[0], "alvo": p2[1][:200]})
        return {"prompt": prompt,
                "resposta": "\n\n".join(resposta),
                "tools": tools}
    return None

# ---------------------------------------------------------------- main

def main():
    arquivos = sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.jsonl")))
    sessoes, eventos_por_sessao = [], {}
    for path in arquivos:
        stats, eventos = processa_sessao(path)
        sessoes.append(stats)
        eventos_por_sessao[stats["id"]] = eventos
        print(f"[ok] {stats['id']}: {stats['msgs_user']} user / "
              f"{stats['msgs_assistant']} assistant / {stats['bash']} bash / "
              f"{stats['arquivos_escritos']} writes")

    sessoes.sort(key=lambda s: s["inicio"] or "")

    momentos = []
    for mid, sprefix, padrao, titulo, valor in MOMENTOS:
        ev = eventos_por_sessao.get(sprefix)
        if not ev:
            print(f"[!!] sessão {sprefix} não encontrada para '{mid}'")
            continue
        m = acha_momento(ev, padrao)
        if not m:
            print(f"[!!] momento '{mid}' não encontrado (padrão: {padrao})")
            continue
        sess = next(s for s in sessoes if s["id"] == sprefix)
        momentos.append({
            "id": mid, "titulo": titulo, "valor": valor,
            "sessao": sprefix, "data": (sess["inicio"] or "")[:10],
            "prompt": m["prompt"],
            "resposta": m["resposta"],
            "tools": m["tools"],
        })
        print(f"[ok] momento '{mid}': prompt {len(m['prompt'])} ch, "
              f"resposta {len(m['resposta'])} ch, {len(m['tools'])} tools")

    g = {
        "n_sessoes": len(sessoes),
        "periodo_inicio": min(s["inicio"] for s in sessoes if s["inicio"])[:10],
        "periodo_fim": max(s["fim"] for s in sessoes if s["fim"])[:10],
        "dias_distintos": len({(s["inicio"] or "")[:10]
                               for s in sessoes if s["inicio"]}),
        "msgs_user": sum(s["msgs_user"] for s in sessoes),
        "msgs_assistant": sum(s["msgs_assistant"] for s in sessoes),
        "comandos_bash": sum(s["bash"] for s in sessoes),
        "arquivos_escritos": sum(s["arquivos_escritos"] for s in sessoes),
        "mb_transcripts": round(sum(
            os.path.getsize(os.path.join(TRANSCRIPT_DIR, s["arquivo"]))
            for s in sessoes) / 1e6, 1),
    }

    out = {"gerado_em": datetime.now().isoformat(timespec="seconds"),
           "stats_globais": g, "sessoes": sessoes, "momentos": momentos}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n[ok] {OUT} gravado — {len(momentos)} momentos, "
          f"{g['n_sessoes']} sessões, {g['comandos_bash']} comandos bash, "
          f"{g['arquivos_escritos']} arquivos escritos")


if __name__ == "__main__":
    main()
