# Sistema-Multi-Agentes

Sistema multiagente para apoiar Engenharia de Requisitos. O projeto recebe
transcrições sintéticas de reuniões com stakeholders, extrai requisitos
candidatos, prepara uma base de conhecimento local e deixa os dados prontos
para análise de ambiguidade, conflito e priorização.

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

