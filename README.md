# ReqLens - Sistema Multiagente de Requisitos

Sistema multiagente para apoiar **Engenharia de Requisitos**. O projeto recebe
transcrições sintéticas de reuniões com stakeholders, extrai requisitos
candidatos, identifica ambiguidades, conflitos e lacunas, prioriza requisitos
com MoSCoW, gera um relatório final rastreável e mantém uma base de
conhecimento local para justificar os achados.

## Assunto Geral Escolhido

Engenharia de Requisitos.

## Problema

Conversas informais com stakeholders frequentemente geram requisitos ambíguos,
incompletos ou conflitantes com decisões já documentadas. O sistema ajuda uma
equipe pequena de software a transformar essas transcrições em artefatos de
requisitos mais claros, revisáveis e rastreáveis.

## Usuário-Alvo

Estudantes, analistas de requisitos e equipes pequenas de desenvolvimento que
precisam revisar requisitos antes de implementar funcionalidades.

## Integrantes

| GitHub Username  | Nome Completo                      | Matrícula    |
| ---------------- | ---------------------------------- | ------------ |
| `BrendaL0pes`    | Brenda Medeiros Lopes              | 2110102949   |
| `samuel-fossari` | Samuel Anthonny Fossari Monteiro   | 2410100276   |
| `gs-Leo`         | Leonardo Goncalves da Silva        | 2510100161   |

## Fluxo Principal

1. O usuário cola uma conversa de stakeholder ou importa uma transcrição `.md`/`.txt`.
2. O agente extrator identifica requisitos funcionais e não funcionais.
3. O agente de ambiguidade procura termos vagos com apoio do corpus.
4. O agente de conflito compara requisitos novos com requisitos existentes.
5. O agente de lacunas identifica regras ausentes ou requisitos incompletos.
6. O agente de priorização atribui MoSCoW.
7. O agente consolidador gera um relatório com rastreabilidade.
8. O resultado é salvo em SQLite e pode ser visto via CLI ou Streamlit.

## Tecnologias

- Python 3.11+
- Agno
- Groq
- Streamlit
- SQLite
- Pytest
- ChromaDB listado como dependência; a indexação atual usa JSON lexical em `vector_store.py`, com `create_chroma_client()` preparado para evolução.

## Agentes Agno

Cada agente é definido em `create_*_agent()` nos módulos `*_agent.py` e executado
via `run_structured_agent()` em `src/req_multiagent/llm_utils.py` quando a LLM
está habilitada. O orquestrador conecta as etapas em
`src/req_multiagent/orchestration/workflow.py`.

| Agente | Arquivo | Papel |
| ------ | ------- | ----- |
| Extrator | `ingestion/extractor_agent.py` | Extrai requisitos da transcrição |
| Ambiguidade | `analysis/ambiguity_agent.py` | Detecta termos vagos com apoio do corpus |
| Conflito | `analysis/conflict_agent.py` | Compara com base existente e lote atual |
| Lacunas | `analysis/gap_agent.py` | Identifica regras ausentes e requisitos incompletos |
| Priorização | `analysis/prioritization_agent.py` | Classifica MoSCoW |
| Consolidador | `orchestration/consolidator_agent.py` | Gera relatório rastreável |
| Atualização de projeto | `orchestration/project_update_agent.py` | Incremento e ajustes via chat (Streamlit) |

Modo determinístico (padrão): regras e heurísticas testáveis, sem chamada à API.
Modo LLM: os mesmos agentes Agno produzem saída estruturada validada por Pydantic.

## Instalação

```bash
uv sync --extra dev
```

O `uv` cria e mantém o ambiente virtual local em `.venv/`. Para ativar
manualmente no Windows:

```bash
.venv\Scripts\activate
```

## Configuração

Copie `.env.example` para `.env`. O pipeline roda **sem API externa** por padrão.
Para usar os agentes Agno com Groq, configure a chave e habilite a LLM.

```env
MODEL_PROVIDER=groq
MODEL_ID=llama-3.3-70b-versatile
USE_LLM_AGENTS=false
GROQ_API_KEY=your-groq-api-key
DATABASE_PATH=storage/requirements.db
KNOWLEDGE_BASE_PATH=storage/knowledge_base
```

Comportamento:

- `USE_LLM_AGENTS=false` (padrão): modo determinístico, reprodutível e sem custo de API.
- `USE_LLM_AGENTS=true` + `GROQ_API_KEY` válida: agentes Agno executam via `agent.run()`.
- `USE_LLM_AGENTS=true` sem chave: fallback automático para o modo determinístico, com aviso no resultado.

Na interface Streamlit, o toggle **Usar LLM Groq** só fica habilitado quando `GROQ_API_KEY` está configurada.

## Execução

Reconstruir a base de conhecimento:

```bash
uv run python scripts/rebuild_knowledge_base.py
```

Executar o pipeline pelo CLI:

```bash
uv run python scripts/run_pipeline.py
```

Executar com uma transcrição específica:

```bash
uv run python scripts/run_pipeline.py data/synthetic_transcripts/transcript_02_support.md
```

Salvar o relatório em Markdown:

```bash
uv run python scripts/run_pipeline.py --output storage/report.md
```

Executar a interface Streamlit:

```bash
uv run streamlit run src/req_multiagent/interface/streamlit_app.py
```

Na interface, a conversa pode ser informada de duas formas:

- Colar o texto diretamente no campo da tela.
- Importar um arquivo com a conversa nos formatos `.md` ou `.txt`.

O sistema aceita conversas naturais. Marcadores como `[RF]` e `[RNF]` continuam
funcionando nos exemplos sintéticos, mas não são obrigatórios na interface.

## Estrutura de Diretórios

```text
data/
  existing_requirements/
  synthetic_transcripts/
docs/
  corpus/
scripts/
src/
  req_multiagent/
    analysis/
    ingestion/
    interface/
    orchestration/
    persistence/
tests/
```

## Fontes de Dados e Corpus

O projeto usa apenas dados sintéticos e documentos didáticos versionados no
repositório.

- `data/synthetic_transcripts/`: transcrições fictícias com casos plantados.
- `data/existing_requirements/`: requisitos fictícios usados para conflitos.
- `docs/corpus/iso29148_criteria.md`: critérios de qualidade de requisitos.
- `docs/corpus/weak_words_ptbr.json`: termos vagos usados na ambiguidade.

Nenhum desses arquivos contém dados pessoais, credenciais, informações
sigilosas ou dados reais de stakeholders.

## Estratégia de Ingestão e Indexação

A ingestão começa em `src/req_multiagent/ingestion/extractor_agent.py`.

- `create_extractor_agent()`: cria o agente Agno de extração.
- `extract_requirements_from_file()`: extrai requisitos dos arquivos sintéticos
  com marcações `[RF]` e `[RNF]`, preservando ID, classificação e fonte.
- `extract_requirements_from_text()`: extrai requisitos de texto colado ou
  importado pela interface usando marcadores explícitos ou heurísticas para
  conversas naturais.

A base de conhecimento local fica em `src/req_multiagent/ingestion/vector_store.py`.
Ela lê documentos de `docs/corpus/` e `data/existing_requirements/`, divide o
conteúdo em blocos por parágrafos e grava um índice local em JSON no caminho
configurado por `KNOWLEDGE_BASE_PATH`. A função `create_chroma_client()` prepara
integração futura com ChromaDB sem alterar os módulos consumidores.

## Estratégia de Análise

A análise fica em `src/req_multiagent/analysis/`. Cada módulo possui um agente
Agno (`create_*_agent()`), funções determinísticas testáveis e variantes LLM
(`*_with_llm`) acionadas pelo workflow quando `resolve_use_llm()` em
`src/req_multiagent/config.py` autoriza o uso da API.

### Agente de Ambiguidade

Arquivo: `src/req_multiagent/analysis/ambiguity_agent.py`

- `detect_ambiguities()`: cruza `weak_words_ptbr.json` com o requisito e consulta
  `iso29148_criteria.md` via RAG local.
- Saída: `AmbiguityFinding` com termo, pergunta de clarificação e evidências.

### Agente de Conflito

Arquivo: `src/req_multiagent/analysis/conflict_agent.py`

- `detect_conflicts()`: compara requisitos extraídos com a base existente e com
  o lote atual.
- `detect_conflicts_with_llm()`: variante Agno para execuções com modelo real.
- Saída: `ConflictFinding` com IDs conflitantes e justificativa.

### Agente de Priorização

Arquivo: `src/req_multiagent/analysis/prioritization_agent.py`

- `prioritize_requirements()`: aplica MoSCoW considerando ambiguidades e conflitos.
- `prioritize_requirements_with_llm()`: variante Agno.
- Regras determinísticas: conflito → `wont`, ambiguidade → `could`, fluxo crítico
  → `must`, demais casos → `should` ou `could`.

### Agente de Lacunas

Arquivo: `src/req_multiagent/analysis/gap_agent.py`

- `detect_gaps()`: identifica trechos narrativos sem regra formal e requisitos
  incompletos em relação à base existente; integrado ao workflow e ao relatório.
- Saída: `GapFinding` com tópico, explicação e perguntas de clarificação.

## Validação da Análise

| Transcrição | Caso plantado | Agente validado |
| ----------- | ------------- | --------------- |
| `transcript_01_checkout.md` | termo vago "rápida" | ambiguidade |
| `transcript_02_support.md` | termo vago "simples" | ambiguidade |
| `transcript_03_approvals.md` | termo vago "eficiente" | ambiguidade |
| `transcript_01_checkout.md` | cancelamento vs. base existente | conflito |
| `transcript_02_support.md` | resposta automática vs. revisão humana | conflito |
| `transcript_03_approvals.md` | sem conflito direto | conflito |
| `transcript_02_support.md` | dúvida narrativa sem regra formal | lacuna |
| `transcript_03_approvals.md` | gestor ausente e registro incompleto | lacuna |
| `transcript_01_checkout.md` | must/could/wont após análise | priorização |

Rodar a suíte completa de testes:

```bash
uv run pytest -v
```

Rodar testes da ingestão, base e análise:

```bash
uv run pytest tests/test_extractor_agent.py tests/test_vector_store.py tests/test_ambiguity_agent.py tests/test_conflict_agent.py tests/test_prioritization_agent.py tests/test_gap_agent.py tests/test_analysis_pipeline.py tests/test_agno_agents.py -v
```

Rodar testes de integração do workflow:

```bash
uv run pytest tests/test_workflow.py -v
```

Os testes determinísticos e de integração não exigem `GROQ_API_KEY`. A suíte atual
conta com 32 testes automatizados.

## Persistência

Os resultados são salvos em SQLite por `src/req_multiagent/persistence/repository.py`.
Por padrão, o banco fica em:

```text
storage/requirements.db
```

Esse estado pode ser apagado com segurança, pois os dados de entrada ficam
versionados em `data/` e `docs/`.

## Checklist Técnico

### Tema e Escopo

- [x] O projeto escolhe um dos assuntos gerais definidos no enunciado: Engenharia de Requisitos.
- [x] O problema resolvido está descrito claramente neste README.
- [x] O usuário-alvo está definido neste README.
- [x] O fluxo principal de uso está descrito neste README.
- [x] O escopo implementado é compatível com o problema proposto.

### Agno e Agentic AI

- [x] O sistema usa Python (`pyproject.toml`, módulos em `src/req_multiagent/`).
- [x] O sistema usa o framework Agno (`agno>=1.4.0`, factories em `*_agent.py`).
- [x] O sistema implementa agentes de extração, ambiguidade, conflito, lacunas, priorização, consolidação e atualização de projeto.
- [x] O uso dos agentes é necessário para o fluxo principal com LLM; o modo determinístico cobre demonstração e testes sem API.
- [x] Prompts/instruções dos agentes estão versionados nos arquivos `*_agent.py`.
- [x] Execução LLM via Agno: `run_structured_agent()` em `llm_utils.py` chama `agent.run(output_schema=...)`.
- [x] O sistema usa workflow (`orchestration/workflow.py`), base de conhecimento (`ingestion/vector_store.py`) e persistência (`persistence/repository.py`).

### Memória, Persistência ou Base de Conhecimento

- [x] O sistema mantém base de conhecimento local e SQLite.
- [x] O estado é armazenado em `storage/`.
- [x] O projeto permite reconstruir a base com `scripts/rebuild_knowledge_base.py`.
- [x] O corpus está documentado em `docs/corpus/`.
- [x] A estratégia de ingestão está documentada neste README.
- [x] A estratégia de chunking/indexação está documentada neste README.
- [x] A resposta indica fontes e evidências usadas.

### Validação e Qualidade da Saída

- [x] O sistema valida saída por regras, corpus, conflitos, lacunas e testes.
- [x] A validação é demonstrável por testes automatizados.
- [x] O sistema informa limitações e casos que exigem revisão humana.

### Interface ou Execução

- [x] O sistema oferece CLI (`scripts/run_pipeline.py`) e Streamlit (`interface/streamlit_app.py`).
- [x] O fluxo principal pode ser executado seguindo este README sem API externa.
- [x] O projeto inclui dados sintéticos em `data/` e comandos de exemplo nesta seção.
- [x] Lacunas aparecem no relatório Markdown, na aba Streamlit e no histórico SQLite.

### Reprodutibilidade

- [x] O repositório contém README.md.
- [x] O repositório contém pyproject.toml.
- [x] O repositório contém .gitignore.
- [x] O repositório contém .env.example.
- [x] O README explica como instalar dependências.
- [x] O README explica como configurar variáveis de ambiente.
- [x] O README explica como executar o sistema.
- [x] O README lista os integrantes.
- [ ] O repositório possui release ou tag da versão entregue.

### Engenharia de Software

- [x] O código está organizado em módulos com responsabilidades claras.
- [x] A lógica dos agentes está separada da interface.
- [x] Configurações e credenciais não estão hardcoded.
- [x] O código usa nomes descritivos.
- [x] O código usa type hints nas assinaturas principais.
- [x] Funções e classes duráveis têm docstrings.
- [x] O projeto possui 32 testes automatizados (`tests/`, comando `uv run pytest -v`).
- [x] O projeto trata erros esperados no fluxo principal.

### Segurança e Dados

- [x] O repositório não contém chaves de API, senhas, tokens ou segredos.
- [x] O repositório não contém dados pessoais sensíveis.
- [x] O projeto usa `.env.example`.
- [x] Dados externos/sintéticos estão descritos neste README.

## Limitações Conhecidas

- A extração de conversa natural usa heurísticas no modo determinístico e pode exigir revisão humana.
- A detecção de ambiguidade depende de `weak_words_ptbr.json` e consulta lexical simples ao corpus ISO 29148.
- A detecção de conflitos cobre padrões explícitos usados na demonstração; a variante LLM pode variar conforme o modelo.
- A detecção de lacunas usa sinais narrativos e regras de completude contra a base existente.
- A priorização MoSCoW usa regras simples no modo determinístico e deve ser revisada por stakeholders.
- A indexação atual da base de conhecimento é JSON lexical; ChromaDB está preparado, mas não é o backend padrão.
- A execução com modelo real depende de `GROQ_API_KEY` e de `USE_LLM_AGENTS=true`.
- O grupo possui 3 integrantes; o enunciado prevê grupos de 4 a 6 — confirmar regularização com o professor.
- A release/tag e o vídeo de apresentação ainda precisam ser criados antes da entrega final.

## Entrega final

Antes de enviar no Moodle:

1. Criar tag ou release no GitHub (`v1.0.0`).
2. Confirmar acesso do professor `paulosevero` ao repositório privado.
3. Gravar vídeo demonstrando tema, fluxo, agentes Agno, persistência e limitações.
4. Enviar link do vídeo e da release/tag no Moodle.
