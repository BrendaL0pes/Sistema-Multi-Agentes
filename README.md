# ReqLens - Sistema Multiagente de Requisitos

Sistema multiagente para apoiar **Engenharia de Requisitos**. O projeto recebe
transcrições sintéticas de reuniões com stakeholders, extrai requisitos
candidatos, prepara uma base de conhecimento local, identifica ambiguidades e
conflitos, prioriza requisitos com MoSCoW e gera um relatório final rastreável.

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
5. O agente de priorização atribui MoSCoW.
6. O agente consolidador gera um relatório com rastreabilidade.
7. O resultado é salvo em SQLite e pode ser visto via CLI ou Streamlit.

## Tecnologias

- Python 3.11+
- Agno
- Groq
- Streamlit
- SQLite
- Pytest
- ChromaDB como dependência preparada para evolução da base vetorial

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

Copie `.env.example` para `.env` e preencha a chave quando for executar agentes
com modelo real.

```env
MODEL_PROVIDER=groq
MODEL_ID=llama-3.3-70b-versatile
USE_LLM_AGENTS=true
GROQ_API_KEY=your-groq-api-key
DATABASE_PATH=storage/requirements.db
KNOWLEDGE_BASE_PATH=storage/knowledge_base
```

Por padrão, o projeto usa a LLM Groq em todos os agentes quando `GROQ_API_KEY`
está configurada. Para rodar sem API externa, desligue a opção **Usar LLM
Groq** na interface ou defina `USE_LLM_AGENTS=false` no `.env`.

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
configurado por `KNOWLEDGE_BASE_PATH`.

## Estratégia de Validação da Saída

A análise fica em `src/req_multiagent/analysis/`.

- `ambiguity_agent.py`: identifica termos fracos e gera perguntas.
- `conflict_agent.py`: compara requisitos novos com requisitos existentes.
- `prioritization_agent.py`: atribui prioridade MoSCoW.

Rodar testes da ingestão, base e análise:

```bash
uv run pytest tests/test_extractor_agent.py tests/test_vector_store.py tests/test_ambiguity_agent.py tests/test_conflict_agent.py tests/test_prioritization_agent.py
```

Rodar teste de integração:

```bash
uv run pytest tests/test_workflow.py
```

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

- [x] O sistema usa Python.
- [x] O sistema usa o framework Agno nos módulos de agentes.
- [x] O sistema implementa agentes de extração, ambiguidade, conflito, priorização e consolidação.
- [x] O uso dos agentes é necessário para o fluxo principal.
- [x] Prompts/instruções dos agentes estão versionados nos arquivos `*_agent.py`.
- [x] O sistema usa workflow, base de conhecimento e persistência.

### Memória, Persistência ou Base de Conhecimento

- [x] O sistema mantém base de conhecimento local e SQLite.
- [x] O estado é armazenado em `storage/`.
- [x] O projeto permite reconstruir a base com `scripts/rebuild_knowledge_base.py`.
- [x] O corpus está documentado em `docs/corpus/`.
- [x] A estratégia de ingestão está documentada neste README.
- [x] A estratégia de chunking/indexação está documentada neste README.
- [x] A resposta indica fontes e evidências usadas.

### Validação e Qualidade da Saída

- [x] O sistema valida saída por regras, corpus, conflitos e testes.
- [x] A validação é demonstrável por testes automatizados.
- [x] O sistema informa limitações e casos que exigem revisão humana.

### Interface ou Execução

- [x] O sistema oferece CLI e Streamlit.
- [x] O fluxo principal pode ser executado seguindo este README.
- [x] O projeto inclui dados e comandos de exemplo.

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
- [x] O projeto possui testes e exemplos executáveis.
- [x] O projeto trata erros esperados no fluxo principal.

### Segurança e Dados

- [x] O repositório não contém chaves de API, senhas, tokens ou segredos.
- [x] O repositório não contém dados pessoais sensíveis.
- [x] O projeto usa `.env.example`.
- [x] Dados externos/sintéticos estão descritos neste README.

## Limitações Conhecidas

- A extração de conversa natural usa heurísticas e pode exigir revisão humana.
- A detecção de conflitos cobre padrões explícitos usados na demonstração.
- A priorização MoSCoW inicial usa regras simples e deve ser revisada por stakeholders.
- A execução com modelo real depende de `GROQ_API_KEY`.
- A release/tag deve ser criada manualmente antes da entrega final.

## Entrega

Consulte `docs/delivery_checklist.md` para a checklist de release/tag e vídeo.
