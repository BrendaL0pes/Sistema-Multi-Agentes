# Especificação de Divisão de Tarefas — Sistema Multiagente de Requisitos

## Critério de divisão

A divisão segue **fatias verticais do pipeline** (não volume de linhas de código),
garantindo que cada pessoa tenha pelo menos um agente Agno funcional sob sua
responsabilidade — relevante para a avaliação individual, que exige domínio
técnico demonstrado e commits com conteúdo significativo.

| | Pessoa A | Pessoa B | Pessoa C |
|---|---|---|---|
| **Papel** | Entrada e Base de Conhecimento | Núcleo de Análise | Orquestração, Interface e Entrega |
| **Agente(s) próprio(s)** | Agente Extrator | Agente de Ambiguidade, Agente de Conflito, Agente de Priorização | Agente Consolidador |
| **Depende de** | — (ponto de partida) | Pessoa A (schema + dados) | Pessoa A e B (integra tudo) |

---

## Pessoa A — Entrada e Base de Conhecimento

### Tarefas
1. Implementar o **Agente Extrator** (`src/req_multiagent/ingestion/extractor_agent.py`):
   recebe transcrição informal, devolve lista de `Requirement` classificados
   como funcional/não-funcional.
2. Implementar o **setup do ChromaDB** (`src/req_multiagent/ingestion/vector_store.py`):
   funções de indexação do corpus normativo e da base de requisitos existentes.
3. Indexar o corpus normativo já fornecido (`docs/corpus/iso29148_criteria.md`,
   `docs/corpus/weak_words_ptbr.json`).
4. Escrever **2-3 transcrições sintéticas de reunião** (`data/synthetic_transcripts/`),
   plantando de propósito: 1 termo ambíguo, 1 conflito, 1 lacuna.
5. Selecionar/adaptar **1 spec existente do grupo** (UniBot, BrifAI, RP5) como base
   de conflito (`data/existing_requirements/`).
6. Escrever `test_extractor_agent.py`.

### Entregáveis concretos
- `ingestion/extractor_agent.py` funcional
- `ingestion/vector_store.py` funcional
- Transcrições sintéticas versionadas
- Base de requisitos existentes versionada
- Teste passando

### Cobre no checklist
- "O corpus ou fonte de dados está documentado"
- "A estratégia de ingestão está documentada"
- "A estratégia de chunking ou indexação está documentada"
- "Dados, documentos ou exemplos versionados no repositório"

---

## Pessoa B — Núcleo de Análise

### Tarefas
1. Implementar o **Agente de Ambiguidade** (`analysis/ambiguity_agent.py`):
   cruza texto do requisito com `weak_words_ptbr.json` + RAG sobre
   `iso29148_criteria.md`, gera perguntas de clarificação.
2. Implementar o **Agente de Conflito** (`analysis/conflict_agent.py`):
   compara requisito novo contra o pool de requisitos (existentes + batch atual),
   retorna IDs conflitantes.
3. Implementar o **Agente de Priorização** (`analysis/prioritization_agent.py`):
   classificação MoSCoW dos requisitos já validados.
4. Escrever `test_ambiguity_agent.py` e `test_conflict_agent.py`, usando os
   problemas plantados pela Pessoa A nas transcrições sintéticas como prova
   de que os agentes detectam corretamente.

### Entregáveis concretos
- Três agentes funcionais em `analysis/`
- Dois arquivos de teste passando, referenciando casos plantados

### Cobre no checklist
- "O sistema tem alguma estratégia para validar, revisar ou justificar a saída gerada"
- "A validação é demonstrável por teste, regra, agente avaliador..."
- "O uso do agente é necessário para o fluxo principal do sistema"

---

## Pessoa C — Orquestração, Interface e Entrega

### Tarefas
1. Implementar o **workflow de orquestração** (`orchestration/workflow.py`):
   conecta extração → análise → consolidação na ordem correta.
2. Implementar o **Agente Consolidador** (`orchestration/consolidator_agent.py`):
   gera documento final com rastreabilidade até a fonte de cada requisito.
3. Implementar a **camada de persistência** (`persistence/repository.py`):
   schema SQLite, save/list de requisitos.
4. Implementar a **interface Streamlit** (`interface/streamlit_app.py`) e o
   **script CLI** (`scripts/run_pipeline.py`).
5. Escrever `test_workflow.py` (teste de integração ponta a ponta).
6. Preencher o **README.md** (integrantes, checklist técnico marcado, limitações
   conhecidas) e o `.env.example` final.
7. Criar a **release/tag** no GitHub e gravar o **vídeo de apresentação**.

### Entregáveis concretos
- `orchestration/workflow.py` e `consolidator_agent.py` funcionais
- `persistence/repository.py` funcional
- Interface Streamlit rodando
- README finalizado com checklist preenchido
- Release/tag criada
- Vídeo gravado

### Cobre no checklist
- "O sistema oferece uma forma clara de uso"
- "O fluxo principal pode ser executado seguindo instruções do README"
- "O repositório possui release ou tag da versão entregue"
- Todos os itens de "Reprodutibilidade"

---

## Cronograma de dependências (hoje é 10/07 — entrega 13/07 23h59)

| Dia | Pessoa A | Pessoa B | Pessoa C |
|---|---|---|---|
| **10/07 (hoje)** | Corpus indexado + 1ª transcrição sintética pronta até o fim do dia | Começa a estruturar prompts dos agentes (sem depender ainda dos dados de A) | Estrutura o workflow com chamadas fake/stub |
| **11/07** | Finaliza transcrições + base de conflito | Implementa e testa os 3 agentes contra os dados de A | Implementa persistência + interface, integra conforme B entrega |
| **12/07** | Apoia testes e ajustes finos | Ajustes finos, garante que os 3 casos plantados são detectados | Integração completa end-to-end, testes de integração |
| **13/07** | Revisão do README/checklist na sua parte | Revisão do README/checklist na sua parte | README final, checklist, release/tag, gravação e envio do vídeo |

## Regra de ouro para a nota individual

Cada pessoa deve commitar diretamente nos arquivos listados como seus
"Entregáveis concretos" acima — commits de formatação, `.gitignore` ou
dependências não contam como contribuição significativa para a avaliação
individual.
