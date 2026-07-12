# Enunciado do Projeto Prático Final

## Tema escolhido

**1. Engenharia de Requisitos**

---

## Condições de conclusão

**Final Boss**

## Descrição

O Projeto Prático Final consiste no planejamento e implementação de um sistema de software que use Agentic AI para apoiar alguma atividade relacionada à Engenharia de Software, ou que aplique boas práticas de Engenharia de Software no desenvolvimento de um sistema baseado em IA.

Diferente dos projetos práticos anteriores, o tema específico do sistema será escolhido por cada grupo. O grupo deve escolher um dos assuntos gerais definidos para o projeto final, delimitar um problema concreto dentro desse assunto e implementar uma solução funcional.

Os assuntos gerais disponíveis são:

- Engenharia de Requisitos.
- Gerenciamento de Projetos de Software.
- DevOps.
- Segurança de Informação.
- Educação Suportada por Inteligência Artificial.
- Gerenciamento de Recursos e Infraestrutura de TI.

O grupo pode escolher livremente o sistema específico a desenvolver dentro de um desses assuntos, desde que o projeto satisfaça os requisitos obrigatórios e tenha relação clara com os conteúdos trabalhados na disciplina.

**IMPORTANTE:** O sistema deve ser implementado em Python com o framework Agno, conforme material disponibilizado na disciplina.

## Escopo Esperado

O projeto final deve ser mais robusto que os Projetos Práticos #01 e #02. Espera-se que o grupo implemente um sistema funcional, demonstrável e reprodutível, e não apenas um protótipo conceitual ou uma coleção de prompts.

O sistema deve:

- Resolver um problema concreto dentro do assunto geral escolhido.
- Ter pelo menos um usuário-alvo claramente definido.
- Usar agentes de IA de forma relevante para o problema.
- Integrar práticas de Engenharia de Software na organização, implementação, documentação e entrega.
- Permitir que o professor execute ou avalie o sistema a partir do repositório entregue.

## Exemplos de Projetos Por Assunto

Os exemplos abaixo são sugestões. O grupo pode propor outro sistema dentro do mesmo assunto, desde que o escopo seja claro, viável e conectado aos conteúdos da disciplina.

### 1. Engenharia de Requisitos

Sistemas que apoiam a elicitação, análise, documentação, validação ou priorização de requisitos.

Exemplos:

- Agente que transforma conversas informais com stakeholders em requisitos funcionais e não funcionais.
- Sistema que identifica ambiguidades, conflitos e lacunas em requisitos textuais.
- Sistema que compara requisitos com issues, pull requests ou documentação.

Escopo fraco:

- Apenas gerar uma lista de requisitos a partir de um prompt único.
- Não validar ambiguidade, conflito, rastreabilidade ou priorização.

### 2. Gerenciamento de Projetos de Software

Sistemas que apoiam planejamento, acompanhamento, estimativa, distribuição de trabalho ou análise de riscos em projetos de software.

Exemplos:

- Sistema que estima esforço e identifica dependências entre tarefas.
- Assistente que analisa andamento de issues e gera relatório de riscos.
- Agente que sugere divisão de tarefas com base em perfis de integrantes.
- Sistema que gera atas, decisões e próximos passos a partir de registros de reunião.

Escopo fraco:

- Apenas gerar um cronograma genérico.
- Não usar dados ou artefatos concretos do projeto.

### 3. DevOps

Sistemas que apoiam automação, integração contínua, entrega contínua, observabilidade, infraestrutura como código ou manutenção operacional.

Exemplos:

- Agente que analisa logs de CI e sugere correções para falhas de build ou teste.
- Sistema que revisa arquivos de pipeline e identifica riscos de configuração.
- Assistente para gerar ou validar Dockerfiles, workflows do GitHub Actions ou scripts de deploy.

Escopo fraco:

- Apenas criar um pipeline simples sem análise inteligente.
- Não demonstrar execução, validação ou inspeção dos artefatos DevOps.

### 4. Segurança de Informação

Sistemas que apoiam identificação, análise, mitigação ou documentação de riscos de segurança.

Exemplos:

- Sistema que revisa dependências e explica vulnerabilidades conhecidas.
- Sistema que gera ataques parametrizáveis para validação e refinamento de sistemas de detecção de intrusão.
- Sistema que transforma achados de segurança em issues priorizadas.

Escopo fraco:

- Apenas listar boas práticas genéricas de segurança.
- Expor, versionar ou processar dados sensíveis reais.

**Atenção:** não use senhas, tokens, chaves privadas, dados pessoais ou informações sigilosas reais. Use exemplos sintéticos.

### 5. Educação Suportada por Inteligência Artificial

Sistemas que apoiam ensino, aprendizagem, tutoria, avaliação formativa ou geração de materiais educacionais.

Exemplos:

- Tutor inteligente que adapta trilhas de aprendizagem conforme o desempenho do estudante.
- Agente que corrige respostas abertas com rubrica explícita e feedback formativo.
- Assistente que transforma material didático em quizzes, exemplos e atividades práticas.

Escopo fraco:

- Apenas gerar perguntas e respostas sem rubrica ou acompanhamento.
- Não demonstrar adaptação, feedback ou validação pedagógica.

### 6. Gerenciamento de Recursos e Infraestrutura de TI

Sistemas que apoiam alocação, monitoramento, planejamento ou otimização de recursos computacionais e infraestrutura.

Exemplos:

- Agente que recomenda alocação de recursos para serviços com base em métricas simuladas.
- Assistente que interpreta alertas de infraestrutura e prioriza incidentes.
- Agente que orquestra operações de manutenção em infraestruturas computacionais.

Escopo fraco:

- Apenas mostrar gráficos estáticos.
- Não ter decisão, recomendação, simulação, explicação ou validação associada aos dados.

## Requisitos Funcionais Mínimos

Cada grupo deve definir os requisitos funcionais específicos do seu sistema. No entanto, todo projeto final deve atender aos seguintes requisitos mínimos:

- **Fluxo principal funcional:** o sistema deve permitir executar pelo menos um fluxo completo de uso relacionado ao problema escolhido.
- **Uso de agente com Agno:** o sistema deve usar pelo menos um agente implementado com Agno.
- **Entrada e saída claras:** o sistema deve receber uma entrada compreensível do usuário ou de uma fonte de dados e produzir uma saída útil para o problema.
- **Persistência, memória ou base de conhecimento:** o sistema deve manter algum tipo de estado, memória, histórico, artefato persistido ou base de conhecimento.
- **Validação da saída:** o sistema deve ter alguma estratégia para verificar, revisar, justificar ou validar a saída gerada. Essa validação pode ser feita por regras, testes, agente avaliador, checagens estruturadas ou comparação com fontes.
- **Interface ou modo de execução demonstrável:** o sistema deve oferecer uma forma clara de uso, como CLI, Streamlit, Gradio, Chainlit, API, bot ou aplicação web.

## Checklist Técnico Obrigatório

O grupo deve copiar este checklist para o README.md do repositório e marcar cada item como atendido ou não atendido. Ao lado de cada item atendido, o grupo deve indicar onde isso aparece no projeto, por exemplo: arquivo, módulo, script, comando, tela ou trecho do vídeo.

### Tema e Escopo

- [ ] O projeto escolhe um dos assuntos gerais definidos no enunciado.
- [ ] O problema resolvido está descrito claramente.
- [ ] O usuário-alvo está definido.
- [ ] O fluxo principal de uso está descrito.
- [ ] O escopo implementado é compatível com o problema proposto.

### Agno e Agentic AI

- [ ] O sistema usa Python.
- [ ] O sistema usa o framework Agno.
- [ ] O sistema implementa pelo menos um agente funcional.
- [ ] O uso do agente é necessário para o fluxo principal do sistema.
- [ ] O prompt, instruções ou configuração do agente estão versionados no repositório.
- [ ] O sistema usa pelo menos uma ferramenta, integração, workflow, time de agentes ou chamada estruturada relacionada ao agente.

### Memória, Persistência ou Base de Conhecimento

- [ ] O sistema mantém algum estado, histórico, memória, base de conhecimento ou artefato persistido.
- [ ] O projeto documenta onde esse estado é armazenado.
- [ ] O projeto permite reconstruir, limpar ou inicializar esse estado quando necessário.

Quando o projeto usar RAG:

- [ ] O corpus ou fonte de dados está documentado.
- [ ] A estratégia de ingestão está documentada.
- [ ] A estratégia de chunking ou indexação está documentada.
- [ ] A resposta indica fontes, trechos ou evidências usadas.

### Validação e Qualidade da Saída

- [ ] O sistema tem alguma estratégia para validar, revisar ou justificar a saída gerada.
- [ ] A validação é demonstrável por teste, regra, agente avaliador, checklist, métrica, comparação com fonte ou revisão estruturada.
- [ ] O sistema informa limitações, incertezas ou casos em que não consegue responder adequadamente.

### Interface ou Execução

- [ ] O sistema oferece uma forma clara de uso, como CLI, Streamlit, Gradio, Chainlit, API, bot ou aplicação web.
- [ ] O fluxo principal pode ser executado seguindo instruções do README.md.
- [ ] O projeto inclui dados de exemplo, prompts de exemplo ou comandos de exemplo para demonstração.

### Reprodutibilidade

- [ ] O repositório contém README.md.
- [ ] O repositório contém pyproject.toml.
- [ ] O repositório contém .gitignore.
- [ ] O repositório contém .env.example.
- [ ] O README.md explica como instalar dependências.
- [ ] O README.md explica como configurar variáveis de ambiente.
- [ ] O README.md explica como executar o sistema.
- [ ] O README.md lista os integrantes com nome, matrícula e username do GitHub.
- [ ] O repositório possui release ou tag da versão entregue.

### Engenharia de Software

- [ ] O código está organizado em módulos ou diretórios com responsabilidades claras.
- [ ] A lógica do agente está separada da interface.
- [ ] Configurações e credenciais não estão hardcoded.
- [ ] O código usa nomes descritivos.
- [ ] O código usa type hints nas assinaturas principais.
- [ ] Funções e classes duráveis têm docstrings.
- [ ] O projeto possui testes, scripts de verificação ou exemplos executáveis.
- [ ] O projeto trata erros esperados no fluxo principal.

### Segurança e Dados

- [ ] O repositório não contém chaves de API, senhas, tokens ou segredos.
- [ ] O repositório não contém dados pessoais sensíveis.
- [ ] O projeto usa .env.example para documentar variáveis de ambiente.
- [ ] Quando usa dados externos, o projeto descreve origem e restrições de uso.

## Práticas Obrigatórias de Engenharia de Software

### Organização e Reprodutibilidade

- Repositório com estrutura de arquivos e diretórios clara e organizada.
- Arquivo README.md com descrição do projeto, integrantes, instruções de instalação, instruções de execução e estrutura de diretórios.
- .gitignore adequado para Python.
- Gerenciamento de dependências baseado em pyproject.toml.
- Arquivo .env.example documentando todas as variáveis de ambiente necessárias.
- Instruções suficientes para executar o fluxo principal do sistema.
- Dados, documentos ou exemplos versionados no repositório quando possível. Quando não for possível, o README.md deve explicar como obter ou reconstruir esses recursos.

### Clean Code

- Código homogêneo em estilo, idioma e formatação.
- Código Python em inglês, seguindo PEP8.
- Nomes descritivos para variáveis, funções, classes, módulos e arquivos.
- Funções curtas e coesas.
- Type hints nas assinaturas.
- Docstrings nas funções e classes duráveis do projeto.

### Princípios de Desenvolvimento

- Separação clara de responsabilidades.
- Baixo acoplamento entre interface, lógica de aplicação, agentes, persistência e integrações externas.
- Configurações e credenciais fora do código-fonte.
- Tratamento explícito de erros nos fluxos principais.
- Testes, scripts de verificação ou exemplos executáveis que ajudem a validar o comportamento do sistema.

## Formação dos Grupos

O trabalho deve ser realizado em grupos de 4 a 6 estudantes.

A formação dos grupos deve ser informada pelo formulário:

<https://forms.gle/mj7YQ3MLk8wakGgN7>

No formulário, o grupo deve informar os integrantes e o link do repositório privado no GitHub já compartilhado com o professor (paulosevero).

Prazo para formação dos grupos: **08/07/2026 às 23h59min**.

Estudantes que não estiverem vinculados a um grupo até o prazo definido estarão sujeitos a nota zero no projeto final.

## Repositório no GitHub

Cada grupo deve criar seu próprio repositório no GitHub. O repositório deve:

- Ser privado.
- Ter como colaboradores somente os integrantes do grupo e, obrigatoriamente, o professor.
- Ser compartilhado com o usuário GitHub paulosevero.
- Conter um README.md com o mapeamento entre username do GitHub, nome completo e matrícula de cada integrante.
- Ter uma release ou tag correspondente à versão entregue.

O professor avaliará a versão marcada pela release ou tag. Se o grupo não criar uma release ou tag, a avaliação poderá considerar a branch principal no momento da correção, sem garantia de que alterações posteriores sejam consideradas.

Se o professor não conseguir acessar o repositório até o prazo de entrega, o projeto poderá receber nota zero por impossibilidade de avaliação.

## Entregáveis

Os entregáveis do Projeto Prático Final são:

- Release ou tag no GitHub contendo o código-fonte e os demais artefatos do projeto.
- Vídeo de apresentação do projeto, com demonstração do sistema funcionando e explicação da implementação.
- README.md completo no repositório, incluindo o checklist técnico preenchido.

O README.md deve conter:

- Nome do projeto.
- Assunto geral escolhido.
- Descrição do problema.
- Usuário-alvo.
- Integrantes do grupo, com nome completo, matrícula e username do GitHub.
- Descrição do fluxo principal do sistema.
- Tecnologias utilizadas.
- Instruções de instalação.
- Instruções de configuração das variáveis de ambiente.
- Instruções de execução.
- Estrutura de diretórios.
- Checklist técnico preenchido.
- Limitações conhecidas.

O vídeo deve demonstrar:

- O problema escolhido e o assunto geral correspondente.
- O usuário-alvo.
- O fluxo principal do sistema funcionando.
- Como o sistema usa Agno e agentes de IA.
- Como o sistema usa memória, persistência ou base de conhecimento.
- Como a saída do sistema é validada.
- Como executar o projeto a partir do repositório.
- Limitações conhecidas.

## Prazo de Entrega

A entrega deve ser feita até **13/07/2026 às 23h59min**, no horário de Brasília.

Entregas após esse prazo não serão aceitas, resultando em nota zero para todo o grupo.

O envio deve ser feito por meio da atividade disponibilizada no Moodle, contendo:

- Link para o vídeo de apresentação.
- Link para a release ou tag no GitHub.

## Critérios de Avaliação

A avaliação seguirá estes grupos de critérios:

O Projeto Prático Final valerá a nota regular prevista para o PPF e incluirá 1 ponto adicional como atividade de recuperação de nota da disciplina. Não haverá outra atividade de recuperação. Esse ponto adicional corresponde à recuperação de desempenho da disciplina e será considerado junto à avaliação do Projeto Prático Final.

### Avaliação por Grupo

- Funcionalidade do sistema.
- Aderência ao checklist técnico.
- Qualidade do código e da arquitetura.
- Reprodutibilidade e documentação.
- Qualidade da demonstração.

### Avaliação Individual

- Domínio técnico demonstrado.
- Contribuição individual comprovada por commits com conteúdo significativo.
- Commits feitos apenas para ajustar formatação, arquivos gerados, dependências ou metadados podem não ser considerados contribuições significativas.
