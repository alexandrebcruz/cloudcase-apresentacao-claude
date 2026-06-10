# CloudCase — Como o Claude construiu o modelo do Consignado

Apresentação interativa em HTML (offline, arquivo único) que mostra, com
trechos verbatim das sessões reais do Claude Code, como o projeto
Consignado (modelo de risco de perda de emprego com RAIS/Novo CAGED) foi
construído do zero — do download dos dados públicos ao treino em GPU e à
apresentação para a diretoria.

## Arquivos

| Arquivo | Papel |
|---|---|
| `extrair_trechos.py` | Minera os transcripts `.jsonl` das sessões do Claude Code e gera `dados_apresentacao.json` (trechos verbatim + estatísticas reais) |
| `dados_apresentacao.json` | Dados extraídos (momentos, sessões, números) |
| `gerar_apresentacao_claude.py` | Gera `apresentacao_claude_consignado.html` a partir do JSON, com figuras reais do projeto embutidas em base64 |
| `apresentacao_claude_consignado.html` | A apresentação — 13 slides, autossuficiente, sem dependências |

## Como regenerar

```bash
python3 extrair_trechos.py        # lê ~/.claude/projects/<projeto>/*.jsonl
python3 gerar_apresentacao_claude.py
```

Abra o HTML no navegador. Navegação: botões à direita, setas do teclado,
PgUp/PgDn, Home/End. Slides interativos: timeline clicável e respostas
expansíveis.

Gerado com Claude Code a partir do histórico real das sessões.
