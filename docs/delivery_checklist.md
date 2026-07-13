# Checklist de Entrega

## Release ou tag

- Criar uma tag ou release no GitHub para a versão entregue.
- Conferir se o professor `paulosevero` tem acesso ao repositório privado.
- Usar a versão marcada pela tag/release como referência no Moodle.

Comando sugerido:

```bash
git tag -a v1.0.0 -m "Entrega Projeto Pratico Final"
git push origin v1.0.0
```

## Vídeo de apresentação

Demonstrar, nesta ordem:

1. Tema escolhido: Engenharia de Requisitos.
2. Usuário-alvo: equipe pequena de software que precisa revisar requisitos.
3. Dados sintéticos e corpus em `data/` e `docs/corpus/`.
4. Execução do CLI com `python scripts/run_pipeline.py`.
5. Execução da interface Streamlit.
6. Extração de requisitos.
7. Detecção de ambiguidade.
8. Detecção de conflito.
9. Priorização MoSCoW.
10. Relatório final com rastreabilidade.
11. Persistência em SQLite.
12. Limitações conhecidas.

## Envio no Moodle

- Link para o vídeo.
- Link para a release ou tag no GitHub.
