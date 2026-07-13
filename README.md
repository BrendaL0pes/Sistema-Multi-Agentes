# Sistema-Multi-Agentes

Sistema multiagente para apoiar Engenharia de Requisitos. O projeto recebe
transcrições sintéticas de reuniões com stakeholders, extrai requisitos
candidatos, analisa ambiguidade, conflito e priorização, e prepara uma base
de conhecimento local para justificar os achados.

## Integrantes

| GitHub Username  | Nome Completo                      | Matrícula    |
| ---------------- | ---------------------------------- | ------------ |
| `BrendaL0pes`    | Brenda Medeiros Lopes              | 2110102949   |
| `samuel-fossari` | Samuel Anthonny Fossari Monteiro   | 2410100276   |
| `gs-Leo`         | Leonardo Goncalves da Silva        | 2510100161   |

## Fontes de dados e corpus

O projeto usa apenas dados sintéticos e documentos didáticos versionados no
repositório.

- `data/synthetic_transcripts/`: transcrições fictícias de reuniões com
  stakeholders. Elas contêm casos plantados de ambiguidade, conflito e lacuna.
- `data/existing_requirements/`: requisitos fictícios já existentes, usados como
  base para comparação e detecção de conflitos.
- `docs/corpus/iso29148_criteria.md`: critérios de qualidade para requisitos,
  como completude, consistência, verificabilidade e rastreabilidade.
- `docs/corpus/weak_words_ptbr.json`: termos vagos em português usados para
  apoiar análise de ambiguidade.

Nenhum desses arquivos contém dados pessoais, credenciais, informações
sigilosas ou dados reais de stakeholders.

## Estratégia de ingestão

A ingestão começa em `src/req_multiagent/ingestion/extractor_agent.py`.

O módulo possui duas partes:

- `create_extractor_agent()`: cria o agente Agno responsável por extrair
  requisitos de transcrições em uma execução com modelo real.
- `extract_requirements_from_file()`: extrai requisitos dos arquivos sintéticos
  versionados usando marcações como `[RF]` e `[RNF]`, preservando ID,
  classificação e rastreabilidade.

Esse desenho permite demonstrar o uso de Agno sem fazer os testes dependerem de
chave de API ou chamada externa.

## Estratégia de indexação

A base de conhecimento local fica sob responsabilidade de
`src/req_multiagent/ingestion/vector_store.py`.

A indexação lê documentos de `docs/corpus/` e `data/existing_requirements/`,
divide o conteúdo em blocos por parágrafos e grava um índice local em JSON no
caminho configurado por `KNOWLEDGE_BASE_PATH`.

Por padrão:

```text
KNOWLEDGE_BASE_PATH=storage/knowledge_base
```

Esse módulo centraliza as operações de:

- inicializar a base local;
- indexar documentos;
- consultar documentos por termos;
- limpar a base;
- reconstruir a base a partir dos arquivos versionados.

## Reconstrução ou limpeza da base

A base de conhecimento é derivada dos arquivos versionados. Portanto, ela pode
ser apagada e reconstruída quando necessário.

Exemplo de uso em Python:

```python
from pathlib import Path

from req_multiagent.ingestion.vector_store import rebuild_knowledge_base

rebuild_knowledge_base(
    source_paths=[
        Path("docs/corpus"),
        Path("data/existing_requirements"),
    ]
)
```

Para limpar manualmente o estado gerado, remova o diretório configurado em
`KNOWLEDGE_BASE_PATH`. O conteúdo fonte continua preservado em `docs/` e
`data/`.

## Estratégia de análise

A análise de requisitos fica em `src/req_multiagent/analysis/`. Cada módulo
possui um agente Agno e funções determinísticas testáveis, no mesmo padrão da
ingestão.

### Agente de Ambiguidade

Arquivo: `src/req_multiagent/analysis/ambiguity_agent.py`

- `create_ambiguity_agent()`: cria o agente Agno responsável por revisar termos
  vagos em execuções com modelo real.
- `detect_ambiguities()`: cruza a descrição do requisito com
  `docs/corpus/weak_words_ptbr.json` e consulta `docs/corpus/iso29148_criteria.md`
  via `vector_store.query_knowledge_base()` para anexar evidências RAG.
- Saída: lista de `AmbiguityFinding` com termo detectado, pergunta de
  clarificação e fontes usadas na justificativa.

### Agente de Conflito

Arquivo: `src/req_multiagent/analysis/conflict_agent.py`

- `create_conflict_agent()`: cria o agente Agno responsável por comparar
  requisitos em execuções com modelo real.
- `load_existing_requirements()`: carrega a base versionada em
  `data/existing_requirements/existing_requirements.md`.
- `detect_conflicts()`: compara requisitos extraídos contra a base existente e
  também contra o lote atual, retornando IDs conflitantes.
- Saída: lista de `ConflictFinding` com explicação e evidências dos dois lados
  da comparação.

### Agente de Priorização

Arquivo: `src/req_multiagent/analysis/prioritization_agent.py`

- `create_prioritization_agent()`: cria o agente Agno responsável por classificar
  requisitos em execuções com modelo real.
- `prioritize_requirements()`: aplica MoSCoW (`must`, `should`, `could`,
  `wont`) considerando ambiguidades e conflitos já detectados.
- Saída: lista de `PriorityAssessment` com prioridade e justificativa.

Regras adotadas na priorização determinística:

- requisitos com conflito viram `wont`;
- requisitos ambíguos viram `could`;
- fluxos funcionais críticos sem problemas viram `must`;
- demais requisitos funcionais e não funcionais são classificados como `should`
  ou `could`, conforme o contexto.

## Validação da análise

A validação da parte de análise é demonstrada por testes automatizados em
`tests/`, usando os casos plantados nas transcrições sintéticas:

| Transcrição | Caso plantado | Agente validado |
| ----------- | ------------- | --------------- |
| `transcript_01_checkout.md` | termo vago "rápida" | ambiguidade |
| `transcript_02_support.md` | termo vago "simples" | ambiguidade |
| `transcript_03_approvals.md` | termo vago "eficiente" | ambiguidade |
| `transcript_01_checkout.md` | cancelamento vs. base existente | conflito |
| `transcript_02_support.md` | resposta automática vs. revisão humana | conflito |
| `transcript_03_approvals.md` | lacuna de aprovação, sem conflito direto | conflito |

Arquivos de teste:

- `tests/test_ambiguity_agent.py`
- `tests/test_conflict_agent.py`

Para executar apenas os testes da análise:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/test_ambiguity_agent.py tests/test_conflict_agent.py -v
```

Esses testes não exigem `GROQ_API_KEY`, porque exercitam a lógica
determinística dos agentes. As funções `create_*_agent()` permanecem
versionadas para demonstração com Agno em execuções com modelo real.

## Limitações conhecidas da análise

- A detecção de ambiguidade depende do dicionário `weak_words_ptbr.json` e de
  consulta lexical simples ao corpus ISO 29148.
- A detecção de conflito usa regras e heurísticas sobre termos-chave; não faz
  comparação semântica profunda entre requisitos.
- A priorização MoSCoW é baseada em sinais textuais e nos achados prévios de
  ambiguidade e conflito; não substitui decisão humana de produto.

