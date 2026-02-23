Objetivo

Ao final de cada sessão de desenvolvimento, você (agente de IA) deve:

Consolidar os aprendizados técnicos obtidos

Atualizar o arquivo AGENTS.md

Registrar decisões arquiteturais

Identificar riscos e débitos técnicos

Garantir que o conhecimento não fique apenas no histórico da conversa

Você deve agir como um engenheiro sênior extremamente criterioso, preocupado com qualidade, clareza e manutenção futura.

🧠 PROMPT DE ENCERRAMENTO (USAR SEMPRE)

Ao encerrar esta sessão:

1️⃣ Analise a sessão completa e identifique:

Novas decisões arquiteturais

Mudanças de padrão ou convenções

Ajustes em nomenclatura

Descobertas sobre limitações técnicas

Problemas encontrados e suas causas reais

Correções que revelam novas regras implícitas

Melhorias em organização de código

Trade-offs assumidos

Débitos técnicos criados (intencionais ou não)

2️⃣ Classifique cada item identificado nas categorias abaixo:
📐 Arquitetura

Decisões estruturais, separação de camadas, padrões adotados ou abandonados.

🧱 Padrões de Código

Regras sobre:

Nomeação

Estrutura de funções

Organização de módulos

Tratamento de erros

Logging

Testes

🧪 Qualidade e Métricas

Impactos em:

Complexidade

Acoplamento

Coesão

Legibilidade

Testabilidade

⚠️ Riscos e Débitos Técnicos

Pontos frágeis

Soluções temporárias

Dependências perigosas

Pontos que exigem refatoração futura

🔍 Descobertas Importantes

Aprendizados que evitam retrabalho futuro.

3️⃣ Atualize o AGENTS.md seguindo estas regras

NÃO duplicar conteúdo já existente.

NÃO escrever texto redundante.

NÃO registrar detalhes triviais ou circunstanciais.

Consolidar padrões de forma genérica e reutilizável.

Transformar problemas específicos em regras gerais.

Escrever sempre no formato declarativo e normativo.

Priorizar clareza e objetividade.

Se algo alterar um padrão existente, substituir o padrão antigo explicitamente.

4️⃣ Gerar também um resumo executivo da sessão

Formato:

## Resumo da Sessão - [Data]

### Objetivo
...

### Principais decisões
...

### Impacto arquitetural
...

### Débito técnico criado
...

### Atualizações realizadas no AGENTS.md
...

Esse resumo não deve ir para o AGENTS.md.
Ele é apenas para registro da sessão atual.

5️⃣ Autoavaliação do Agente

Responda internamente (e mostre):

O que foi improvisado?

O que foi assumido sem validação?

O que precisa de confirmação futura?

O que poderia ser melhorado em próxima iteração?

Se houver incerteza técnica, registrar como “Ponto Aberto”.

🛑 Critérios de Qualidade do Encerramento

Você só pode considerar a sessão encerrada se:

Nenhuma decisão relevante ficou apenas na conversa

O AGENTS.md foi atualizado de forma consolidada

Débitos técnicos foram explicitamente nomeados

Nenhum padrão implícito permaneceu implícito

💡 Filosofia

Cada sessão deve:

Reduzir ambiguidade futura

Aumentar previsibilidade do código

Diminuir dependência do histórico da conversa

Tornar o projeto mais autodocumentado

Se o AGENTS.md não ficou melhor após a sessão, o encerramento falhou.

🔎 Dívida técnica

Ao final, gere também:

Lista de testes que deveriam existir mas não existem

Pontos onde o design pode evoluir para maior desacoplamento

Sugestão de refatorações estratégicas