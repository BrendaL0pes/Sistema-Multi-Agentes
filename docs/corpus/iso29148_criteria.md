# Critérios de Qualidade para Requisitos

Este corpus resume critérios práticos de qualidade usados para revisar requisitos de software. Ele foi preparado para fins didáticos e deve ser usado como base de conhecimento local do projeto.

## Critério: Necessário

Um requisito deve representar uma necessidade real do usuário, do negócio ou de uma restrição relevante do sistema.

Evidências esperadas:

- O requisito está ligado a um objetivo do usuário ou stakeholder.
- O requisito não descreve apenas uma preferência genérica.
- A ausência do requisito causaria perda funcional, risco ou retrabalho.

## Critério: Não Ambíguo

Um requisito deve ter uma única interpretação razoável.

Sinais de problema:

- Uso de palavras vagas como rápido, fácil, intuitivo, adequado ou eficiente.
- Falta de unidade de medida, limite, condição ou contexto.
- Termos que dependem de julgamento subjetivo sem critério verificável.

## Critério: Completo

Um requisito deve conter informação suficiente para ser entendido, implementado e validado.

Evidências esperadas:

- Atores ou usuários envolvidos estão claros.
- Condições de entrada e saída são compreensíveis.
- Regras de negócio importantes estão explícitas.
- Exceções ou restrições relevantes são citadas.

## Critério: Consistente

Um requisito não deve contradizer outro requisito ou regra existente.

Sinais de problema:

- Um requisito permite uma ação que outro proíbe.
- Dois requisitos definem comportamentos diferentes para a mesma condição.
- Uma regra nova invalida uma restrição já documentada sem registrar decisão.

## Critério: Verificável

Um requisito deve poder ser testado, medido ou inspecionado.

Evidências esperadas:

- O resultado esperado é observável.
- Há critério de aceite, métrica, limite ou exemplo.
- Uma pessoa avaliadora conseguiria decidir se o requisito foi atendido.

## Critério: Rastreável

Um requisito deve preservar ligação com sua origem.

Evidências esperadas:

- Há referência ao documento, transcrição, reunião ou stakeholder de origem.
- O trecho que motivou o requisito pode ser localizado.
- Mudanças futuras podem ser comparadas com a fonte original.
