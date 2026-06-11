# ClaudeCase — Como o Claude construiu o modelo do Consignado

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
| `gerar_apresentacao_claude.py` | Gera as apresentações a partir do JSON, com figuras reais do projeto embutidas em base64 |
| `apresentacao_claude_consignado.html` | A apresentação técnica — 19 slides, autossuficiente, sem dependências |
| `apresentacao_claude_consignado_executivo.html` | Variante para público leigo (diretoria/executivos) — 17 slides |
| `fonts_dejavu.css` | Fonte DejaVu Sans embutida (base64), mesma do deck original |

## Como regenerar

```bash
python3 extrair_trechos.py                      # lê ~/.claude/projects/<projeto>/*.jsonl
python3 gerar_apresentacao_claude.py            # versão técnica
python3 gerar_apresentacao_claude.py --executivo  # versão para diretoria
```

Abra o HTML no navegador.

## Versão executiva (`--executivo`)

Adaptada para quem não trabalha com ciência de dados:

- **Jargão traduzido**: sem CatBoost/Kaplan-Meier/holdout/tokens — "modelo de
  IA treinado em supercomputadores alugados por hora", "quanto tempo cada
  pessoa tende a permanecer empregada", "X mi de páginas lidas e escritas"
- **Resultado primeiro**: novo slide "O problema de negócio" e a tabela de
  cobertura de parcelas logo no início; bastidores depois
- **Números como comparação de negócio**: 6 dias vs. 3–6 meses de um projeto
  típico; custo = 1 mês de assinatura vs. computação avulsa
- **3 momentos em vez de 6** (controle de risco, método, entrega) + slide
  resumo "os outros momentos em uma linha"
- **Slide de Governança**: LGPD/dados públicos, humano no comando,
  auditabilidade, próximos passos
- **Cortado**: heatmap dia × hora; o slide de energia/data centers foi
  mantido em versão adaptada (tom ESG: eficiência crescente, matriz limpa,
  "usar bem")
- **Sem revelação progressiva**: todos os blocos já aparecem abertos (bom
  para envio por e-mail). Na versão técnica, o mesmo efeito pode ser obtido
  abrindo o arquivo com `?modo=executivo` na URL

## Navegação e recursos

- Botões à direita, setas do teclado, espaço, PgUp/PgDn, Home/End
- **Revelação progressiva**: nos slides de conversa, cada avanço revela a
  próxima bolha (com efeito "digitando…")
- **F** alterna tela cheia; pontinhos no rodapé pulam direto para um slide
- Barra de progresso laranja no rodapé; transição suave entre slides
- Timeline clicável (sessões reais), heatmap de atividade dia × hora,
  gráfico de mensagens por sessão e output real de comando no slide de
  anatomia — tudo com dados medidos dos transcripts
- `Ctrl+P` imprime um slide por página (exportável em PDF)

Gerado com Claude Code a partir do histórico real das sessões.
