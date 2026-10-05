# Apresentação da solução

A apresentação atual é `delivery/BanVic-Apresentacao-Certificacao.pptx`, revisada em **05/10/2026**. Ela possui dez slides e reúne arquitetura, execução, reconciliação, falhas, segurança, consumo comercial e limites da inferência. O arquivo original `BanVic-Apresentacao-Final.pptx` foi preservado como registro da etapa anterior.

## Conteúdo conferido

1. Escopo da POC: sete tabelas, 76.206 linhas e 30 testes aprovados.
2. Arquitetura de ingestão e publicação, com diagrama editável.
3. Deploy, acesso e primeira execução, na ordem correta.
4. Interface real do Airflow e resultado da revisão atual.
5. Reconciliação das sete tabelas, com tabela nativa.
6. Recuperação, idempotência e rollback.
7. Segredos, acesso somente leitura e limites do ambiente local.
8. Reprodução do projeto pelos scripts e README.
9. Indicadores comerciais do último trimestre completo do ERP.
10. Prioridade exploratória de validação e ausência de causalidade identificada.

A imagem do Airflow no slide 4 registra a execução anterior `certification_demo`, de 04/10, com 49,023 s. Uma legenda distingue essa captura do resultado atual: `review3_20261005_final`, de 05/10, concluído em 55,826 s. A nova execução foi conferida pela API e no navegador. Não se apresenta uma imagem histórica como captura de uma nova execução.

## Validação

Os dez slides finais foram renderizados e inspecionados individualmente. A exportação passou pelas verificações de integridade do PPTX, geometria, fontes, importação e presença de quatro tabelas nativas nos slides 5, 6, 9 e 10. As tabelas, os textos e o diagrama permanecem editáveis; a captura de tela é uma imagem. O recibo público está em `evidence/review3/presentation-validation.json`.

Não houve teste de edição dentro do Microsoft PowerPoint ou Google Slides. A verificação confirma a estrutura e a renderização no runtime utilizado, sem afirmar comportamento idêntico em todos os aplicativos.

## Reproduzir os slides

O pipeline não depende do runtime de apresentação. `scripts/build_presentation.mjs` reconstrói o deck histórico de oito slides; `scripts/revise_presentation.mjs` importa esse deck, mantém sua estrutura e acrescenta a revisão comercial.

A revisão usa o runtime de artefatos e os validadores da habilidade Presentations. Configure caminhos absolutos para `SKILL_DIR`, `RUNTIME_NODE_MODULES`, `RUNTIME_PYTHON`, `WORKSPACE_DIR`, `TMP_DIR`, `SOURCE_PPTX` e `FINAL_PPTX`. A fonte é o PPTX original e a saída deve usar um nome novo, em `delivery/`. Use um diretório privado de build novo a cada exportação, com `node_modules` ligado aos módulos do runtime. Copie o script para esse diretório e execute com o Node do runtime.

O script lê `evidence/review3/review3_20261005_final.json`; os dados comerciais e a origem das afirmações são citados nas notas dos slides. O recibo de validação e as imagens de revisão ficam no diretório privado de build. O script não grava ou gera vídeo.

## Entrega e escopo do vídeo

Entregue o ZIP de código e a apresentação atual como arquivos separados, conforme a opção da plataforma. O ZIP exclui a fonte oficial, segredos, estado local e arquivos de mídia. A conferência completa está em [REVISAO_FINAL_REQUISITOS.md](REVISAO_FINAL_REQUISITOS.md).

O enunciado exige vídeo de três a cinco minutos. Por solicitação do usuário, esta revisão não gravou, narrou, editou, gerou ou verificou vídeo. O arquivo e o roteiro anteriores foram preservados; não integram as conclusões de validação atual. Não houve submissão automática na plataforma.
