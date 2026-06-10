#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera apresentacao_claude_consignado.html — apresentação interativa sobre
como o Claude Code foi usado para construir o projeto Consignado, com
trechos reais das sessões (dados_apresentacao.json, via extrair_trechos.py)
e figuras reais do projeto embutidas em base64.

Layout baseado na apresentação existente do Consignado
(gerar_apresentacao_html.py): palco 16:9, navy #14233f, laranja #f4a722,
HTML autossuficiente, sem dependências externas.
"""
import base64
import html
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = "/mnt/d/Projetos/Consignado/outputs/figures"
DADOS = json.load(open(os.path.join(BASE, "dados_apresentacao.json"),
                       encoding="utf-8"))
OUT = os.path.join(BASE, "apresentacao_claude_consignado.html")

G = DADOS["stats_globais"]
SESSOES = DADOS["sessoes"]
MOMENTOS = {m["id"]: m for m in DADOS["momentos"]}

MESES = {"01": "jan", "02": "fev", "03": "mar", "04": "abr", "05": "mai",
         "06": "jun", "07": "jul", "08": "ago", "09": "set", "10": "out",
         "11": "nov", "12": "dez"}


def e(t):
    return html.escape(t or "", quote=False)


# Traduções de respostas que estavam em inglês no histórico
# (conteúdo idêntico, apenas vertido para português)
TRADUCOES = {
    "gpu": """Vou começar entendendo a configuração atual de treino do ensemble com lags, e então planejar os ajustes de parâmetros.

Nenhum pod está rodando (o `pod.json` está desatualizado). Eis o que encontrei:

- A rodada anterior com lags parou cedo na **iteração 70 (A) / 95 (B)** com `depth=8, learning_rate=0.08` — muito abaixo da sua meta de 1000. Para empurrar a melhor iteração para ~1000 preciso **reduzir o learning rate ~10×** e **diminuir a profundidade** (aprendizado mais lento e menos propenso a overfit).
- A parte cara (construir e quantizar os dois pools de 132M/148M linhas) é **independente de depth/LR**, então vou construir os pools **uma única vez** e iterar barato só na etapa de `fit`.

Vou deixar o script parametrizável (ler depth/LR de variáveis de ambiente, manter os pools em disco entre os fits) antes de subir qualquer máquina.

O script agora é configurável por variáveis de ambiente (`LAGS_DEPTH`, `LAGS_LR`), mantém os pools em disco entre os fits para reajustar barato e retreina a cada execução. A construção dos pools (a etapa pesada de RAM) acontece uma vez; depois itero apenas no `fit` na GPU.

Antes de subir a B200 (o CLAUDE.md exige confirmar pods pagos, e esta é a de US$ 5,89/h), uma decisão sobre como rodar o loop de tuning:

Estratégia confirmada (calibrar no A, replicar). Vou subir a B200 e começar.

Os parâmetros precisam ficar aninhados sob a chave `params`:

Pod `5jfqm6utgon35b` (B200, US$ 5,89/h) está RODANDO. Vou organizar o acompanhamento das tarefas e aguardar o SSH.

SSH disponível em `207.210.107.252:12174`. Gravando o pod.json e criando as tarefas.

Agora vou verificar a conexão SSH e instalar as dependências no pod.

Preciso de um Python local com paramiko. Vou checar o ambiente.

B200 confirmada: 183 GB de VRAM, RAM de sobra. Instalando as dependências agora.

Dependências OK (catboost 1.2.10). Agora vou conferir os caminhos locais dos dados antes de sincronizar.

Dados presentes (~3,5 GB de interim 2019–2023 + 19 MB de agregados). Vou checar os caminhos esperados pelos scripts de sync e preparação.

Caminhos confirmados. Vou subir primeiro o código e os agregados de lags (rápido), e depois rodar sozinho o sync grande do interim.

Agregados sincronizados. Agora o sync grande do interim (2019–2023, ~3,5 GB) — rodando sozinho em background, como o guia do projeto exige.

Sync rodando em background. Vou acompanhar o progresso sem disparar processos concorrentes.

O sync do interim está rodando em background; vou aguardar a conclusão antes de prosseguir (disparar outros comandos poderia derrubá-lo, segundo o guia do projeto). Continuo automaticamente quando terminar.

30 arquivos candidatos, sync em andamento (reconectando sozinho nas quedas). Aguardando a conclusão.

Agendei uma checagem. Aguardando o sync terminar (a tarefa em background também vai me avisar quando concluir)."""
}


for _mid, _txt in TRADUCOES.items():
    if _mid in MOMENTOS:
        MOMENTOS[_mid]["resposta"] = _txt


# ----------------------------------------------------- markdown → HTML

def md_html(t):
    """Conversor leve de markdown (negrito, código, títulos, listas,
    tabelas) para HTML — suficiente para as respostas do Claude."""
    linhas = t.split("\n")
    out, i = [], 0
    para, lista = [], []

    def inline(s):
        s = html.escape(s, quote=False)
        s = re.sub(r"`([^`]+)`", r'<code class="mdc">\1</code>', s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", s)
        return s

    def flush_para():
        if para:
            out.append("<p>" + "<br>".join(inline(x) for x in para) + "</p>")
            para.clear()

    def flush_lista():
        if lista:
            out.append('<ul class="mdl">' +
                       "".join(f"<li>{inline(x)}</li>" for x in lista) +
                       "</ul>")
            lista.clear()

    while i < len(linhas):
        ln = linhas[i].rstrip()
        s = ln.strip()
        # tabela
        if s.startswith("|") and s.endswith("|") and s.count("|") >= 2:
            flush_para(); flush_lista()
            rows = []
            while i < len(linhas):
                s2 = linhas[i].strip()
                if not (s2.startswith("|") and s2.count("|") >= 2):
                    break
                cels = [c.strip() for c in s2.strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cels):
                    rows.append(cels)
                i += 1
            if rows:
                thead = ("<tr>" + "".join(f"<th>{inline(c)}</th>"
                         for c in rows[0]) + "</tr>")
                tbody = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>"
                                for c in r) + "</tr>" for r in rows[1:])
                out.append(f'<table class="mdt"><thead>{thead}</thead>'
                           f"<tbody>{tbody}</tbody></table>")
            continue
        # título
        mh = re.match(r"^(#{1,4})\s+(.*)$", s)
        if mh:
            flush_para(); flush_lista()
            out.append(f'<div class="mdh">{inline(mh.group(2))}</div>')
            i += 1
            continue
        # item de lista (com ou sem número)
        ml = re.match(r"^(?:[-•]|\d+[.)])\s+(.*)$", s)
        if ml:
            flush_para()
            lista.append(ml.group(1))
            i += 1
            continue
        # linha vazia = quebra de parágrafo
        if not s:
            flush_para(); flush_lista()
            i += 1
            continue
        flush_lista()
        para.append(s)
        i += 1
    flush_para(); flush_lista()
    return "".join(out)


def fmt_data(iso):
    if not iso:
        return ""
    d = iso[:10]
    return f"{d[8:10]}/{MESES.get(d[5:7], d[5:7])}"


def fmt_n(n):
    return f"{n:,}".replace(",", ".")


def img_b64(nome):
    """PNG real do projeto embutido em base64."""
    path = os.path.join(FIGDIR, nome)
    with open(path, "rb") as f:
        b = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b}"


# ------------------------------------------------------- SVGs ilustrativos

SVG_PLAN = '''<svg viewBox="0 0 360 300" xmlns="http://www.w3.org/2000/svg">
<style>.f{fill:#f4f7fb;stroke:#cbd6e6;rx:6}.t{font:600 13px sans-serif;fill:#14233f}
.s{font:11px sans-serif;fill:#5b6675}.l{stroke:#cbd6e6;stroke-width:1.5}</style>
<rect class="f" x="100" y="8" width="160" height="34" rx="6"/>
<text class="t" x="180" y="30" text-anchor="middle">Consignado/</text>
<line class="l" x1="180" y1="42" x2="180" y2="58"/>
<line class="l" x1="50" y1="58" x2="310" y2="58"/>
<line class="l" x1="50" y1="58" x2="50" y2="70"/><line class="l" x1="137" y1="58" x2="137" y2="70"/>
<line class="l" x1="223" y1="58" x2="223" y2="70"/><line class="l" x1="310" y1="58" x2="310" y2="70"/>
<rect class="f" x="10" y="70" width="80" height="30" rx="6"/>
<text class="s" x="50" y="89" text-anchor="middle">data/raw</text>
<rect class="f" x="97" y="70" width="80" height="30" rx="6"/>
<text class="s" x="137" y="89" text-anchor="middle" textLength="68"
 lengthAdjust="spacingAndGlyphs">notebooks/</text>
<rect class="f" x="183" y="70" width="80" height="30" rx="6"/>
<text class="s" x="223" y="89" text-anchor="middle">src/</text>
<rect class="f" x="270" y="70" width="80" height="30" rx="6"/>
<text class="s" x="310" y="89" text-anchor="middle">outputs/</text>
<line class="l" x1="137" y1="100" x2="137" y2="112"/>
<g font="11px sans-serif">
<rect x="50" y="112" width="240" height="22" rx="4" fill="#14233f"/>
<text x="170" y="127" text-anchor="middle" fill="#fff" font-size="10.5">01_download_dados.ipynb</text>
<rect x="50" y="139" width="240" height="22" rx="4" fill="#1f3a66"/>
<text x="170" y="154" text-anchor="middle" fill="#fff" font-size="10.5" textLength="215" lengthAdjust="spacingAndGlyphs">02_limpeza_harmonizacao.ipynb</text>
<rect x="50" y="166" width="240" height="22" rx="4" fill="#2c5f9e"/>
<text x="170" y="181" text-anchor="middle" fill="#fff" font-size="10.5">03_features_lags.ipynb</text>
<rect x="50" y="193" width="240" height="22" rx="4" fill="#3b7dba"/>
<text x="170" y="208" text-anchor="middle" fill="#fff" font-size="10.5" textLength="215" lengthAdjust="spacingAndGlyphs">… 08_scoring_validacao.ipynb</text>
</g>
<rect x="10" y="236" width="340" height="48" rx="8" fill="#fdf6e7" stroke="#f4a722" stroke-width="2"/>
<text x="180" y="256" text-anchor="middle" font-size="10.5" font-weight="700" fill="#b07b10" textLength="310" lengthAdjust="spacingAndGlyphs">ESCOPO FECHADO ANTES DO CÓDIGO</text>
<text x="180" y="273" text-anchor="middle" font-size="10" fill="#5b6675" textLength="300" lengthAdjust="spacingAndGlyphs">granularidade · horizonte · validação · LGPD</text>
</svg>'''

SVG_PGFN = '''<svg viewBox="0 0 360 300" xmlns="http://www.w3.org/2000/svg">
<style>.b{fill:#f4f7fb;stroke:#cbd6e6;stroke-width:1.5}.t{font:600 12px sans-serif;fill:#14233f}
.s{font:10.5px sans-serif;fill:#5b6675}.a{stroke:#f4a722;stroke-width:2.5;fill:none;marker-end:url(#ar)}</style>
<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
<path d="M0,0 L8,4 L0,8 z" fill="#f4a722"/></marker></defs>
<rect class="b" x="14" y="16" width="200" height="56" rx="8"/>
<text class="t" x="114" y="38" text-anchor="middle" textLength="178" lengthAdjust="spacingAndGlyphs">Dados Abertos PGFN</text>
<text class="s" x="114" y="56" text-anchor="middle" textLength="182" lengthAdjust="spacingAndGlyphs">Dívida Ativa · trimestral · CSV</text>
<rect class="b" x="14" y="86" width="200" height="56" rx="8"/>
<text class="t" x="114" y="108" text-anchor="middle">Lista de Devedores</text>
<text class="s" x="114" y="126" text-anchor="middle" textLength="180" lengthAdjust="spacingAndGlyphs">listadevedores.pgfn.gov.br</text>
<rect class="b" x="14" y="156" width="200" height="56" rx="8"/>
<text class="t" x="114" y="178" text-anchor="middle">Certidão (CND)</text>
<text class="s" x="114" y="196" text-anchor="middle">situação fiscal oficial</text>
<path class="a" d="M214,44 C265,44 265,100 288,108"/>
<path class="a" d="M214,114 C250,114 260,114 288,114"/>
<path class="a" d="M214,184 C265,184 265,128 288,120"/>
<rect x="252" y="84" width="100" height="60" rx="8" fill="#14233f" transform="rotate(0)"/>
<text x="302" y="108" text-anchor="middle" font-size="11.5" font-weight="700" fill="#fff">CNPJ →</text>
<text x="302" y="126" text-anchor="middle" font-size="11.5" font-weight="700" fill="#f4a722">flag dívida</text>
<rect x="14" y="234" width="332" height="52" rx="8" fill="#fdf6e7" stroke="#f4a722" stroke-width="2"/>
<text x="180" y="255" text-anchor="middle" font-size="10.5" font-weight="700" fill="#b07b10" textLength="300" lengthAdjust="spacingAndGlyphs">PREVIDENCIÁRIO · FGTS · DEMAIS TRIBUTOS</text>
<text x="180" y="273" text-anchor="middle" font-size="9.5" fill="#5b6675" textLength="305" lengthAdjust="spacingAndGlyphs">3 fontes mapeadas, com limitações e LGPD, em uma resposta</text>
</svg>'''

SVG_CAT = '''<svg viewBox="0 0 360 300" xmlns="http://www.w3.org/2000/svg">
<style>.h{font:700 13px sans-serif;fill:#fff}.c{font:600 12px monospace;fill:#14233f}
.s{font:11px sans-serif;fill:#5b6675}</style>
<rect x="14" y="14" width="155" height="34" rx="6" fill="#3b7dba"/>
<text class="h" x="91" y="36" text-anchor="middle">RAIS 2021</text>
<rect x="191" y="14" width="155" height="34" rx="6" fill="#2c5f9e"/>
<text class="h" x="268" y="36" text-anchor="middle">RAIS 2023</text>
<g>
<rect x="14" y="58" width="155" height="30" rx="5" fill="#f4f7fb" stroke="#cbd6e6"/>
<text class="c" x="91" y="78" text-anchor="middle" textLength="136" lengthAdjust="spacingAndGlyphs">01 = Analfabeto</text>
<rect x="191" y="58" width="155" height="30" rx="5" fill="#f4f7fb" stroke="#cbd6e6"/>
<text class="c" x="268" y="78" text-anchor="middle" textLength="140" lengthAdjust="spacingAndGlyphs">01 = Analfabeto ✓</text>
<rect x="14" y="96" width="155" height="30" rx="5" fill="#f4f7fb" stroke="#cbd6e6"/>
<text class="c" x="91" y="116" text-anchor="middle" textLength="140" lengthAdjust="spacingAndGlyphs">05 = Fund. completo</text>
<rect x="191" y="96" width="155" height="30" rx="5" fill="#fde8e6" stroke="#d73027"/>
<text class="c" x="268" y="116" text-anchor="middle" fill="#d73027" textLength="140" lengthAdjust="spacingAndGlyphs">05 = ≠ significado ✗</text>
<rect x="14" y="134" width="155" height="30" rx="5" fill="#f4f7fb" stroke="#cbd6e6"/>
<text class="c" x="91" y="154" text-anchor="middle">10 = Mestrado</text>
<rect x="191" y="134" width="155" height="30" rx="5" fill="#fde8e6" stroke="#d73027"/>
<text class="c" x="268" y="154" text-anchor="middle" fill="#d73027" textLength="140" lengthAdjust="spacingAndGlyphs">10 = ≠ significado ✗</text>
</g>
<circle cx="180" cy="111" r="17" fill="#f4a722"/>
<text x="180" y="118" text-anchor="middle" font-size="18" font-weight="700" fill="#14233f">≠</text>
<rect x="14" y="190" width="332" height="44" rx="8" fill="#14233f"/>
<text x="180" y="209" text-anchor="middle" font-size="11.5" font-weight="700" fill="#f4a722" textLength="262" lengthAdjust="spacingAndGlyphs">SOLUÇÃO: DE-PARA POR ANO</text>
<text x="180" y="226" text-anchor="middle" font-size="9.5" fill="#cdd9ea" textLength="305" lengthAdjust="spacingAndGlyphs">dicionários versionados harmonizam os códigos antes do modelo</text>
<text class="s" x="180" y="262" text-anchor="middle" textLength="320" lengthAdjust="spacingAndGlyphs">Sem essa checagem, o modelo aprenderia padrões falsos —</text>
<text class="s" x="180" y="278" text-anchor="middle">e nenhum erro apareceria no código.</text>
</svg>'''

SVG_BALANCO = '''<svg viewBox="0 0 360 300" xmlns="http://www.w3.org/2000/svg">
<style>.t{font:600 11.5px sans-serif;fill:#14233f}.s{font:10.5px sans-serif;fill:#5b6675}
.a{stroke:#f4a722;stroke-width:2.5;fill:none;marker-end:url(#ar2)}</style>
<defs><marker id="ar2" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
<path d="M0,0 L8,4 L0,8 z" fill="#f4a722"/></marker></defs>
<circle cx="62" cy="74" r="16" fill="#14233f"/>
<path d="M36,118 a26,22 0 0 1 52,0 z" fill="#14233f"/>
<text class="t" x="62" y="142" text-anchor="middle">1 pessoa</text>
<text x="62" y="172" text-anchor="middle" font-size="22" font-weight="700" fill="#f4a722">+</text>
<rect x="30" y="186" width="64" height="40" rx="9" fill="#f4a722"/>
<text x="62" y="211" text-anchor="middle" font-size="15" font-weight="800" fill="#14233f">✳</text>
<text class="t" x="62" y="246" text-anchor="middle" textLength="96" lengthAdjust="spacingAndGlyphs">Claude Code</text>
<path class="a" d="M104,150 C140,150 140,46 166,42"/>
<path class="a" d="M104,150 C145,150 145,116 166,113"/>
<path class="a" d="M104,150 C145,150 145,186 166,184"/>
<path class="a" d="M104,150 C140,150 140,256 166,255"/>
<g>
<rect x="170" y="22" width="178" height="42" rx="8" fill="#f4f7fb" stroke="#cbd6e6"/>
<text class="t" x="259" y="40" text-anchor="middle">Engenharia de dados</text>
<text class="s" x="259" y="56" text-anchor="middle">RAIS + CAGED, vários anos</text>
<rect x="170" y="93" width="178" height="42" rx="8" fill="#f4f7fb" stroke="#cbd6e6"/>
<text class="t" x="259" y="111" text-anchor="middle">Infra &amp; GPU remota</text>
<text class="s" x="259" y="127" text-anchor="middle">B200/H200, jobs monitorados</text>
<rect x="170" y="164" width="178" height="42" rx="8" fill="#f4f7fb" stroke="#cbd6e6"/>
<text class="t" x="259" y="182" text-anchor="middle">Estatística &amp; modelo</text>
<text class="s" x="259" y="198" text-anchor="middle">CatBoost, KM, Weibull</text>
<rect x="170" y="235" width="178" height="42" rx="8" fill="#f4f7fb" stroke="#cbd6e6"/>
<text class="t" x="259" y="253" text-anchor="middle">Comunicação</text>
<text class="s" x="259" y="269" text-anchor="middle">apresentação para a diretoria</text>
</g>
</svg>'''

SVG_COVER = '''<svg viewBox="0 0 300 420" xmlns="http://www.w3.org/2000/svg" opacity="0.5">
<g fill="none" stroke="#3b7dba" stroke-width="2">
<rect x="60" y="30" width="200" height="58" rx="14"/>
<path d="M88,88 l-12,20 l30,-20" fill="none"/>
</g>
<g fill="none" stroke="#f4a722" stroke-width="2">
<rect x="20" y="140" width="200" height="58" rx="14"/>
<path d="M192,198 l12,20 l-30,-20"/>
</g>
<g fill="none" stroke="#3b7dba" stroke-width="2">
<rect x="60" y="250" width="200" height="58" rx="14"/>
<path d="M88,308 l-12,20 l30,-20"/>
</g>
<g stroke="#9fc0e8" stroke-width="2" opacity="0.7">
<line x1="80" y1="52" x2="180" y2="52"/><line x1="80" y1="68" x2="230" y2="68"/>
<line x1="40" y1="162" x2="160" y2="162"/><line x1="40" y1="178" x2="190" y2="178"/>
<line x1="80" y1="272" x2="200" y2="272"/><line x1="80" y1="288" x2="160" y2="288"/>
</g>
<text x="150" y="392" text-anchor="middle" font-size="58" font-weight="800" fill="#f4a722">✳</text>
</svg>'''


# ------------------------------------------------------------ componentes

def header(kicker, titulo):
    return (f'<div class="hb"><div class="kick">{e(kicker)}</div>'
            f'<div class="ttl">{e(titulo)}</div></div>')


def chat_user(texto, max_ch=420):
    t = texto.strip()
    curto = t if len(t) <= max_ch else t[:max_ch].rsplit(" ", 1)[0] + " …"
    return (f'<div class="row ru"><div class="bub bu">'
            f'<div class="who">VOCÊ</div>{e(curto)}</div></div>')


def trunca_md(t, max_ch):
    """Trunca texto markdown próximo de max_ch, em fronteira de
    parágrafo (para não quebrar tabelas/listas no meio)."""
    if len(t) <= max_ch:
        return t, False
    blocos = t.split("\n\n")
    acc = []
    tot = 0
    for b in blocos:
        if acc and tot + len(b) > max_ch:
            break
        acc.append(b)
        tot += len(b) + 2
    curto = "\n\n".join(acc).strip()
    if len(curto) > max_ch * 1.6:  # primeiro bloco gigante: corta na palavra
        curto = curto[:max_ch].rsplit(" ", 1)[0] + " …"
    return curto, True


def chat_claude(texto, max_ch=560):
    t = texto.strip()
    curto, truncado = trunca_md(t, max_ch)
    if not truncado:
        corpo = f'<span class="rsh">{md_html(t)}</span>'
        btn = ""
    else:
        corpo = (f'<span class="rsh">{md_html(curto)}</span>'
                 f'<span class="rfull" hidden>{md_html(t)}</span>')
        btn = (f'<button class="more" onclick="expande(this)">'
               f'ver resposta completa</button>')
    return (f'<div class="row rc"><div class="bub bc md">'
            f'<div class="who whoc">CLAUDE</div>{corpo}{btn}</div></div>')


def term_block(tools, max_tools=3):
    if not tools:
        return ""
    linhas = []
    for t in tools[:max_tools]:
        alvo = t["alvo"].replace("\n", " ")
        if len(alvo) > 86:
            alvo = alvo[:86] + " …"
        ic = {"Bash": "$", "Write": "+", "Edit": "±", "Read": "›",
              "NotebookEdit": "±"}.get(t["tool"], "·")
        linhas.append(f'<div class="tl"><span class="tt">{e(t["tool"])}'
                      f'</span> <span class="tp">{ic}</span> {e(alvo)}</div>')
    return f'<div class="term">{"".join(linhas)}</div>'


def figbox(conteudo, cap, real=False):
    cls = "figbox figreal" if real else "figbox"
    return (f'<div class="{cls}"><div class="figin">{conteudo}</div>'
            f'<div class="figcap">{e(cap)}</div></div>')


def fig_img(nome, cap):
    return figbox(f'<img src="{img_b64(nome)}" alt="">', cap, real=True)


def slide_momento(num, total, m, kicker, fig_html, resp_ch=520):
    return f'''
<section class="slide">
 {header(kicker, m["titulo"])}
 <div class="body">
  <div class="cols">
   <div class="colL">
    <div class="chatcol">
     {chat_user(m["prompt"])}
     {chat_claude(m["resposta"], resp_ch)}
     {term_block(m["tools"])}
    </div>
   </div>
   <div class="colR">{fig_html}</div>
  </div>
  <div class="why"><span class="wlbl">POR QUE ISSO IMPORTA</span> {e(m["valor"])}
   <span class="src">sessão {m["sessao"]} · {fmt_data(m["data"])} · trecho verbatim do histórico</span>
  </div>
 </div>
 <div class="foot">Momento {num} de {total} · conversas reais extraídas das sessões do Claude Code</div>
</section>'''


# ------------------------------------------------------------ slides

slides = []

# 1 — capa
slides.append(f'''
<section class="slide cover">
 <div class="cdec">{SVG_COVER}</div>
 <div class="cbox">
  <div class="ckick">PROJETO CONSIGNADO · BASTIDORES</div>
  <div class="ctit">COMO O CLAUDE CONSTRUIU<br>O MODELO DE RISCO</div>
  <div class="csub">Do download dos dados públicos ao treino em GPU e à apresentação
  para a diretoria — tudo conduzido por conversa, em português.</div>
  <div class="cmeta">{fmt_data(G["periodo_inicio"]+"T")} – {fmt_data(G["periodo_fim"]+"T")} ·
  {G["n_sessoes"]} sessões de trabalho · trechos reais do histórico</div>
 </div>
</section>''')

# 2 — o projeto em 1 slide (bullets + figura real)
slides.append(f'''
<section class="slide">
 {header("CONTEXTO", "O projeto em um slide")}
 <div class="body">
  <div class="cols">
   <div class="colL">
    <ul class="big">
     <li><b>Objetivo:</b> estimar o risco de perda de emprego nos próximos meses, só com dados públicos (RAIS + Novo CAGED), para subsidiar o crédito consignado.</li>
     <li><b>Pipeline:</b> download dos microdados oficiais (FTP do MTE), limpeza, harmonização entre anos e features com lags.</li>
     <li><b>Modelo:</b> ensemble CatBoost treinado em GPUs B200/H200, calibrado, com 23 categorias de risco.</li>
     <li><b>Análises:</b> sobrevivência Kaplan-Meier, extrapolação Weibull, personas por categoria.</li>
     <li><b>Entrega:</b> apresentação interativa em HTML usada com a diretoria.</li>
    </ul>
   </div>
   <div class="colR">
    {fig_img("sobrevivencia_categorias_2023.png",
             "Saída real do projeto: curvas de sobrevivência das 23 categorias de risco")}
   </div>
  </div>
  <div class="why"><span class="wlbl">O PONTO</span> Cada uma dessas etapas foi feita pedindo ao Claude — esta apresentação mostra como.</div>
 </div>
 <div class="foot">Projeto: D:/Projetos/Consignado</div>
</section>''')

# 3 — números reais
cards = [
    (str(G["n_sessoes"]), "sessões de trabalho"),
    ("6 dias", f'{fmt_data(G["periodo_inicio"]+"T")} a {fmt_data(G["periodo_fim"]+"T")}'),
    (fmt_n(G["msgs_user"]), "pedidos feitos em português"),
    (fmt_n(G["msgs_assistant"]), "respostas e ações do Claude"),
    (fmt_n(G["comandos_bash"]), "comandos executados"),
    (fmt_n(G["arquivos_escritos"]), "arquivos criados ou editados"),
]
cards_html = "".join(
    f'<div class="card"><div class="cn">{e(v)}</div>'
    f'<div class="cl">{e(l)}</div></div>' for v, l in cards)
slides.append(f'''
<section class="slide">
 {header("NÚMEROS REAIS", "O que aconteceu nas sessões — medido, não estimado")}
 <div class="body">
  <div class="cards">{cards_html}</div>
  <div class="why"><span class="wlbl">FONTE</span> Estatísticas extraídas diretamente dos
  {G["mb_transcripts"]} MB de histórico das sessões do Claude Code deste projeto — nada aqui é estimativa.</div>
 </div>
 <div class="foot">Extraído de ~/.claude/projects/…Consignado/*.jsonl</div>
</section>''')

# 4 — timeline interativa
sess_js = []
for s in SESSOES:
    sess_js.append({
        "id": s["id"], "desc": s["descricao"], "data": fmt_data(s["inicio"]),
        "msgs": s["msgs_user"] + s["msgs_assistant"],
        "user": s["msgs_user"], "bash": s["bash"],
        "writes": s["arquivos_escritos"],
        "prompt": (s["primeiro_prompt"] or "")[:420],
        "pedidos": s.get("pedidos", []),
    })
slides.append(f'''
<section class="slide">
 {header("LINHA DO TEMPO", "As 8 sessões — clique para ver como cada uma começou")}
 <div class="body">
  <div class="tlbar" id="tlbar"></div>
  <div class="tlpanel" id="tlpanel">
   <div class="tlhint">▲ Clique em uma sessão acima para ver os detalhes e o primeiro pedido verbatim.</div>
  </div>
 </div>
 <div class="foot">Tamanho dos blocos proporcional ao volume de mensagens da sessão</div>
</section>''')

# 5 — anatomia de um turno (usa o momento "ftp")
ftp = MOMENTOS["ftp"]
slides.append(f'''
<section class="slide">
 {header("COMO FUNCIONA", "A anatomia de uma interação")}
 <div class="body">
  <div class="steps">
   <div class="step"><div class="sn">1</div>Você pede,<br>em português</div>
   <div class="arr">→</div>
   <div class="step"><div class="sn">2</div>O Claude investiga<br>e executa comandos</div>
   <div class="arr">→</div>
   <div class="step"><div class="sn">3</div>Analisa os resultados<br>e responde com evidência</div>
  </div>
  <div class="chatcol">
   {chat_user(ftp["prompt"])}
   {term_block(ftp["tools"], 2)}
   {chat_claude(ftp["resposta"], 380)}
  </div>
  <div class="why"><span class="wlbl">EXEMPLO REAL</span> {e(ftp["valor"])}
   <span class="src">sessão {ftp["sessao"]} · {fmt_data(ftp["data"])}</span></div>
 </div>
 <div class="foot">O Claude não responde de memória: ele conecta no FTP, lista as datas e prova a resposta</div>
</section>''')

# 6–11 — momentos de ouro (chat à esquerda, figura à direita)
FIGS_MOMENTO = {
    "planejamento": figbox(SVG_PLAN,
        "O que saiu desse prompt: estrutura completa do projeto, 8 notebooks e escopo fechado"),
    "pgfn": figbox(SVG_PGFN,
        "As 3 fontes públicas da PGFN mapeadas na resposta"),
    "categoricas": figbox(SVG_CAT,
        "O risco: o mesmo código com significados diferentes entre anos"),
    "gpu": fig_img("calibracao_ensemble_base.png",
        "Figura real do projeto: calibração do ensemble treinado na B200"),
    "tempo_medio": fig_img("sobrevivencia_weibull_extrap_2023.png",
        "Resultado da conversa: extrapolação Weibull do tempo até desligamento"),
    "html_interativo": fig_img("estatisticas_tempo_categorias_2023.png",
        "Figura real do projeto: estatísticas de tempo por categoria de risco"),
}
ORDEM = ["planejamento", "pgfn", "categoricas", "gpu",
         "tempo_medio", "html_interativo"]
KICKERS = {
    "planejamento": "MOMENTO 1 · PLANEJAMENTO",
    "pgfn": "MOMENTO 2 · PESQUISA",
    "categoricas": "MOMENTO 3 · QUALIDADE DE DADOS",
    "gpu": "MOMENTO 4 · TREINO EM GPU",
    "tempo_medio": "MOMENTO 5 · MÉTODO",
    "html_interativo": "MOMENTO 6 · ENTREGA",
}
for i, mid in enumerate(ORDEM, 1):
    slides.append(slide_momento(i, len(ORDEM), MOMENTOS[mid],
                                KICKERS[mid], FIGS_MOMENTO[mid]))

# 12 — o que não seria viável (bullets + SVG)
slides.append(f'''
<section class="slide">
 {header("BALANÇO", "O que não seria viável sem isso")}
 <div class="body">
  <div class="cols">
   <div class="colL">
    <ul class="big">
     <li><b>Escala:</b> microdados da RAIS e do CAGED de vários anos baixados, validados e processados — {fmt_n(G["comandos_bash"])} comandos executados sem digitar nenhum à mão.</li>
     <li><b>Infraestrutura:</b> provisionamento, treino e monitoramento em GPUs B200/H200 remotas, com jobs longos em background.</li>
     <li><b>Amplitude:</b> a mesma conversa cobre estatística, engenharia de dados, tuning de CatBoost e front-end.</li>
     <li><b>Velocidade com rigor:</b> do primeiro prompt à apresentação para a diretoria em 6 dias.</li>
     <li><b>Memória do processo:</b> todo o raciocínio ficou registrado — esta apresentação veio do próprio histórico.</li>
    </ul>
   </div>
   <div class="colR">
    {figbox(SVG_BALANCO, "Uma pessoa cobrindo quatro papéis de um time de dados")}
   </div>
  </div>
 </div>
 <div class="foot">Uma pessoa + Claude Code = um time de dados de ponta a ponta</div>
</section>''')

# 13 — encerramento
slides.append(f'''
<section class="slide cover">
 <div class="cdec">{SVG_COVER}</div>
 <div class="cbox">
  <div class="ckick">PARA FECHAR</div>
  <div class="ctit">TUDO ISSO FOI FEITO<br>CONVERSANDO.</div>
  <div class="csub">Nenhum dos {fmt_n(G["comandos_bash"])} comandos foi digitado à mão.
  Nenhuma linha dos {fmt_n(G["arquivos_escritos"])} arquivos foi escrita sozinha.
  O trabalho foi dirigir: perguntar, decidir e validar.</div>
  <div class="cmeta">E sim — esta própria apresentação também foi gerada pelo Claude,
  lendo o histórico real das sessões.</div>
 </div>
</section>''')

SLIDES_HTML = "\n".join(slides)
SESS_JSON = json.dumps(sess_js, ensure_ascii=False)

# ------------------------------------------------------------ template

HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Como o Claude construiu o modelo do Consignado</title>
<style>
:root{--u:min(1vw,1.7778vh);--navy:#14233f;--ink:#1b2430;--gray:#5b6675;
--orange:#f4a722;--blue:#3b7dba;--lblue:#9fc0e8;}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:#0d1626;
font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;color:var(--ink)}
#stage{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);
width:min(100vw,177.78vh);height:min(56.25vw,100vh);background:#fff;
overflow:hidden;box-shadow:0 0 calc(var(--u)*4) rgba(0,0,0,.6)}
.slide{position:absolute;inset:0;display:none;background:#fff}
.slide.active{display:block}
/* header */
.hb{position:absolute;top:0;left:0;right:0;height:14%;background:var(--navy);
border-left:calc(var(--u)*0.55) solid var(--orange);display:flex;
flex-direction:column;justify-content:center;padding-left:2.6%}
.kick{color:var(--lblue);font-weight:700;letter-spacing:.06em;
font-size:calc(var(--u)*1.15)}
.ttl{color:#fff;font-weight:700;font-size:calc(var(--u)*2.0)}
.body{position:absolute;top:15.5%;left:2.6%;right:7.5%;bottom:8%;
display:flex;flex-direction:column;gap:calc(var(--u)*0.9)}
.foot{position:absolute;bottom:1.6%;left:2.6%;right:7.5%;color:var(--gray);
font-size:calc(var(--u)*0.85);border-top:1px solid #e3e7ee;
padding-top:calc(var(--u)*0.4)}
/* colunas */
.cols{display:flex;gap:calc(var(--u)*1.4);flex:1;min-height:0}
.colL{flex:1.15;display:flex;flex-direction:column;min-width:0;min-height:0}
.colR{flex:0.85;display:flex;flex-direction:column;min-width:0;min-height:0}
/* figuras */
.figbox{flex:1;display:flex;flex-direction:column;background:#f9fafc;
border:1px solid #e0e6ef;border-radius:10px;padding:calc(var(--u)*0.9);
min-height:0}
.figin{flex:1;display:flex;align-items:center;justify-content:center;
min-height:0}
.figin svg{width:100%;height:100%;max-height:100%}
.figin img{max-width:100%;max-height:100%;object-fit:contain;
border-radius:6px}
.figcap{color:var(--gray);font-size:calc(var(--u)*0.85);text-align:center;
overflow-wrap:anywhere;
padding-top:calc(var(--u)*0.55);border-top:1px solid #e8edf4;
margin-top:calc(var(--u)*0.55)}
.figreal .figcap::before{content:'FIGURA REAL DO PROJETO · ';
color:#b07b10;font-weight:700;letter-spacing:.05em;
font-size:calc(var(--u)*0.7)}
/* capa */
.cover{background:var(--navy)}
.cdec{position:absolute;right:3%;top:10%;bottom:10%;width:26%;opacity:.55;
overflow:hidden}
.cdec svg{width:100%;height:100%}
.cbox{position:absolute;left:7%;top:24%;right:32%}
.ckick{color:var(--orange);font-weight:700;letter-spacing:.14em;
font-size:calc(var(--u)*1.25);margin-bottom:calc(var(--u)*1.6)}
.ctit{color:#fff;font-weight:700;font-size:calc(var(--u)*3.4);
line-height:1.12;margin-bottom:calc(var(--u)*1.8);
border-left:calc(var(--u)*0.55) solid var(--orange);
padding-left:calc(var(--u)*1.6)}
.csub{color:#cdd9ea;font-size:calc(var(--u)*1.4);line-height:1.5;
margin-bottom:calc(var(--u)*2.2)}
.cmeta{color:var(--lblue);font-size:calc(var(--u)*1.05)}
/* bullets grandes */
.big{list-style:none;display:flex;flex-direction:column;
justify-content:center;flex:1;
gap:calc(var(--u)*1.05);font-size:calc(var(--u)*1.22);line-height:1.42}
.big li{padding-left:calc(var(--u)*1.5);position:relative;
overflow-wrap:anywhere}
.big li::before{content:'';position:absolute;left:0;top:calc(var(--u)*0.45);
width:calc(var(--u)*0.62);height:calc(var(--u)*0.62);background:var(--orange);
border-radius:2px}
/* cards de números */
.cards{display:grid;grid-template-columns:repeat(3,1fr);
gap:calc(var(--u)*1.2);flex:1;align-content:center}
.card{background:#f4f7fb;border:1px solid #dfe6f0;border-radius:8px;
border-top:calc(var(--u)*0.4) solid var(--orange);text-align:center;
padding:calc(var(--u)*1.6) calc(var(--u)*0.8);display:flex;
flex-direction:column;justify-content:center;gap:calc(var(--u)*0.5)}
.cn{font-size:calc(var(--u)*3.1);font-weight:700;color:var(--navy);
font-variant-numeric:tabular-nums}
.cl{font-size:calc(var(--u)*1.05);color:var(--gray)}
/* chat */
.chatcol{display:flex;flex-direction:column;gap:calc(var(--u)*0.7);
flex:1;min-height:0;overflow:auto;padding-right:calc(var(--u)*0.5)}
.row{display:flex}
.ru{justify-content:flex-end}
.rc{justify-content:flex-start}
.bub{max-width:92%;border-radius:10px;padding:calc(var(--u)*0.9) calc(var(--u)*1.2);
font-size:calc(var(--u)*1.04);line-height:1.45;white-space:pre-wrap;
overflow-wrap:anywhere;min-width:0;overflow:hidden}
.bu{background:var(--navy);color:#eaf0f8;border-bottom-right-radius:2px}
.bc{background:#f6f8fb;border:1px solid #e0e6ef;
border-left:calc(var(--u)*0.4) solid var(--orange);
border-bottom-left-radius:2px;color:var(--ink)}
.bc.md{white-space:normal}
.bc.md p{margin:calc(var(--u)*0.45) 0}
.bc.md p:first-of-type{margin-top:0}
.mdh{font-weight:700;color:var(--navy);font-size:calc(var(--u)*1.08);
margin:calc(var(--u)*0.7) 0 calc(var(--u)*0.3);
border-bottom:2px solid var(--orange);display:inline-block;
padding-bottom:calc(var(--u)*0.1)}
.mdl{margin:calc(var(--u)*0.4) 0 calc(var(--u)*0.4) calc(var(--u)*1.4);
display:flex;flex-direction:column;gap:calc(var(--u)*0.3)}
.mdl li::marker{color:var(--orange)}
.mdc{font-family:'Cascadia Code',Consolas,Menlo,monospace;
font-size:0.92em;background:#e9eef6;color:#1f3a66;border-radius:4px;
padding:0 calc(var(--u)*0.3);overflow-wrap:anywhere;word-break:break-all}
.bu .mdc{background:rgba(255,255,255,.14);color:#ffd790}
.mdt{border-collapse:collapse;margin:calc(var(--u)*0.5) 0;
font-size:calc(var(--u)*0.92);width:100%;table-layout:fixed}
.mdt th{background:var(--navy);color:#fff;font-weight:600;
padding:calc(var(--u)*0.25) calc(var(--u)*0.55);text-align:left;
overflow-wrap:anywhere}
.mdt td{border:1px solid #dde4ee;background:#fff;
padding:calc(var(--u)*0.25) calc(var(--u)*0.55);overflow-wrap:anywhere}
.mdt tr:nth-child(even) td{background:#f4f7fb}
.who{font-size:calc(var(--u)*0.78);font-weight:700;letter-spacing:.08em;
color:var(--lblue);margin-bottom:calc(var(--u)*0.35)}
.whoc{color:var(--orange)}
.more{display:block;margin-top:calc(var(--u)*0.6);background:none;
border:1px solid var(--blue);color:var(--blue);border-radius:5px;
padding:calc(var(--u)*0.25) calc(var(--u)*0.8);cursor:pointer;
font-size:calc(var(--u)*0.85)}
.more:hover{background:var(--blue);color:#fff}
/* terminal */
.term{background:#0d1626;border-radius:8px;
padding:calc(var(--u)*0.8) calc(var(--u)*1.1);
font-family:'Cascadia Code',Consolas,Menlo,monospace;
font-size:calc(var(--u)*0.9);color:#c9d6e8;flex-shrink:0}
.tl{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
line-height:1.7}
.tt{color:var(--orange);font-weight:700}
.tp{color:#5b8bc4}
/* faixa de valor */
.why{background:#fdf6e7;border:1px solid #f0ddb0;border-radius:8px;
padding:calc(var(--u)*0.8) calc(var(--u)*1.1);font-size:calc(var(--u)*1.05);
line-height:1.4;flex-shrink:0;overflow-wrap:anywhere;overflow:hidden}
.wlbl{color:#b07b10;font-weight:700;font-size:calc(var(--u)*0.8);
letter-spacing:.08em;margin-right:calc(var(--u)*0.5)}
.src{display:block;color:var(--gray);font-size:calc(var(--u)*0.82);
margin-top:calc(var(--u)*0.3)}
/* timeline */
.tlbar{display:flex;gap:calc(var(--u)*0.45);align-items:stretch;
height:calc(var(--u)*8);flex-shrink:0}
.tseg{border-radius:7px;background:var(--blue);color:#fff;cursor:pointer;
display:flex;flex-direction:column;justify-content:center;align-items:center;
gap:calc(var(--u)*0.2);min-width:calc(var(--u)*6);border:none;
transition:transform .12s}
.tseg:hover{transform:translateY(calc(var(--u)*-0.3))}
.tseg.sel{background:var(--orange);color:var(--navy)}
.td1{font-weight:700;font-size:calc(var(--u)*1.0)}
.td2{font-size:calc(var(--u)*0.78);opacity:.85}
.tlpanel{flex:1;background:#f6f8fb;border:1px solid #e0e6ef;border-radius:8px;
padding:calc(var(--u)*1.2);overflow:auto}
.tlhint{color:var(--gray);font-size:calc(var(--u)*1.05)}
.tph{font-weight:700;color:var(--navy);font-size:calc(var(--u)*1.35);
margin-bottom:calc(var(--u)*0.5)}
.tpm{color:var(--gray);font-size:calc(var(--u)*0.95);
margin-bottom:calc(var(--u)*0.8)}
.tpq{background:var(--navy);color:#eaf0f8;border-radius:8px;
border-bottom-right-radius:2px;padding:calc(var(--u)*0.9) calc(var(--u)*1.1);
font-size:calc(var(--u)*1.0);line-height:1.45;white-space:pre-wrap;
overflow-wrap:anywhere;overflow:hidden}
.tpq .who{margin-bottom:calc(var(--u)*0.3)}
.tpcols{display:flex;gap:calc(var(--u)*1.2);align-items:flex-start}
.tpc1{flex:0.9;min-width:0}
.tpc2{flex:1.1;min-width:0}
.plbl{color:#b07b10;font-weight:700;font-size:calc(var(--u)*0.8);
letter-spacing:.08em;margin-bottom:calc(var(--u)*0.55)}
.peds{list-style:none;display:flex;flex-direction:column;
gap:calc(var(--u)*0.5)}
.peds li{position:relative;padding:calc(var(--u)*0.5) calc(var(--u)*0.8)
 calc(var(--u)*0.5) calc(var(--u)*2.6);background:#fff;
border:1px solid #e0e6ef;border-left:calc(var(--u)*0.35) solid var(--blue);
border-radius:6px;font-size:calc(var(--u)*0.94);line-height:1.4;
color:var(--ink);overflow-wrap:anywhere;overflow:hidden}
.pn{position:absolute;left:calc(var(--u)*0.7);top:50%;
transform:translateY(-50%);width:calc(var(--u)*1.4);
height:calc(var(--u)*1.4);border-radius:50%;background:var(--blue);
color:#fff;font-weight:700;font-size:calc(var(--u)*0.8);text-align:center;
line-height:calc(var(--u)*1.4)}
/* passos */
.steps{display:flex;align-items:center;gap:calc(var(--u)*1.0);
justify-content:center;flex-shrink:0}
.step{background:#f4f7fb;border:1px solid #dfe6f0;border-radius:8px;
padding:calc(var(--u)*0.7) calc(var(--u)*1.2);text-align:center;
font-size:calc(var(--u)*0.98);line-height:1.3}
.sn{display:block;margin:0 auto calc(var(--u)*0.4);
background:var(--orange);color:var(--navy);
font-weight:700;width:calc(var(--u)*1.7);height:calc(var(--u)*1.7);
border-radius:50%;line-height:calc(var(--u)*1.7);
font-size:calc(var(--u)*1.0)}
.arr{color:var(--orange);font-size:calc(var(--u)*1.8);font-weight:700}
/* navegação lateral direita */
#nav{position:absolute;right:1.1%;top:50%;transform:translateY(-50%);
display:flex;flex-direction:column;gap:calc(var(--u)*0.8);align-items:center;
z-index:50}
.nbtn{width:calc(var(--u)*3.2);height:calc(var(--u)*3.2);border-radius:50%;
border:none;background:var(--navy);color:#fff;font-size:calc(var(--u)*1.7);
cursor:pointer;opacity:.85;line-height:1}
.nbtn:hover{background:var(--orange);color:var(--navy);opacity:1}
.nbtn:disabled{opacity:.25;cursor:default}
#counter{color:var(--gray);font-size:calc(var(--u)*0.9);
font-variant-numeric:tabular-nums;background:rgba(255,255,255,.88);
border:1px solid #dfe6f0;
border-radius:6px;padding:calc(var(--u)*0.2) calc(var(--u)*0.5)}
</style>
</head>
<body>
<div id="stage">
@@SLIDES@@
<div id="nav">
 <button class="nbtn" id="bprev" onclick="go(-1)" title="Anterior (←)">‹</button>
 <div id="counter">1 / 1</div>
 <button class="nbtn" id="bnext" onclick="go(1)" title="Próximo (→)">›</button>
</div>
</div>
<script>
const SESS=@@SESS@@;
const slides=[...document.querySelectorAll('.slide')];let cur=0;
const counter=document.getElementById('counter');
const bp=document.getElementById('bprev'),bn=document.getElementById('bnext');
function show(n){cur=Math.max(0,Math.min(slides.length-1,n));
 slides.forEach((s,i)=>s.classList.toggle('active',i===cur));
 counter.textContent=(cur+1)+' / '+slides.length;
 bp.disabled=cur===0;bn.disabled=cur===slides.length-1;}
function go(d){show(cur+d);}
document.addEventListener('keydown',e=>{
 if(e.key==='ArrowRight'||e.key==='PageDown')go(1);
 else if(e.key==='ArrowLeft'||e.key==='PageUp')go(-1);
 else if(e.key==='Home')show(0);
 else if(e.key==='End')show(slides.length-1);});
show(0);
/* expandir resposta completa */
function expande(btn){
 const b=btn.parentElement,sh=b.querySelector('.rsh'),
       f=b.querySelector('.rfull');
 const aberto=!f.hidden;
 f.hidden=aberto;sh.hidden=!aberto;
 btn.textContent=aberto?'ver resposta completa':'recolher';}
/* timeline */
const bar=document.getElementById('tlbar'),
      panel=document.getElementById('tlpanel');
if(bar){
 const tot=SESS.reduce((a,s)=>a+s.msgs,0);
 SESS.forEach((s,i)=>{
  const b=document.createElement('button');b.className='tseg';
  b.style.flex=String(Math.max(s.msgs/tot,0.045));
  b.innerHTML='<span class="td1">'+s.data+'</span>'+
              '<span class="td2">'+s.msgs+' msgs</span>';
  b.onclick=()=>{
   [...bar.children].forEach(x=>x.classList.remove('sel'));
   b.classList.add('sel');
   let peds=(s.pedidos||[]).map((p,j)=>
    '<li><span class="pn">'+(j+1)+'</span>'+esc(p)+'</li>').join('');
   if(!peds)peds='<li>Sessão curta e direta: o primeiro pedido ao lado '+
    'resume a conversa inteira.</li>';
   const plbl=(s.pedidos||[]).length>1?
    s.pedidos.length+' PRINCIPAIS PEDIDOS SEGUINTES (ORDEM CRONOLÓGICA)':
    'PEDIDOS SEGUINTES';
   panel.innerHTML='<div class="tph">'+s.desc+'</div>'+
    '<div class="tpm">Sessão '+s.id+' · '+s.data+' · '+s.user+
    ' pedidos · '+s.bash+' comandos · '+s.writes+' arquivos</div>'+
    '<div class="tpcols">'+
     '<div class="tpc1"><div class="tpq">'+
      '<div class="who">PRIMEIRO PEDIDO DA SESSÃO (VERBATIM)</div>'+
      esc(s.prompt)+'</div></div>'+
     '<div class="tpc2"><div class="plbl">'+plbl+'</div>'+
      '<ol class="peds">'+peds+'</ol></div>'+
    '</div>';};
  bar.appendChild(b);});}
function esc(t){const d=document.createElement('div');
 d.textContent=t;return d.innerHTML;}
</script>
</body>
</html>"""

html_final = HTML.replace("@@SLIDES@@", SLIDES_HTML).replace(
    "@@SESS@@", SESS_JSON)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html_final)

n_slides = SLIDES_HTML.count('<section class="slide')
print(f"[ok] {OUT} gerado — {n_slides} slides, "
      f"{os.path.getsize(OUT)/1048576:.1f} MB")
