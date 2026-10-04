# Roteiro do vídeo técnico BanVic

Versão narrada com capturas reais e cortes de tempo. Voz sintética local. Para gravar sua própria voz, use o texto abaixo e mantenha a demonstração entre 3 e 5 minutos.

## 00:00 a 00:22 — Projeto BanVic

Esta Ã© a prova de conceito de engenharia de dados do BanVic. O projeto centraliza as sete tabelas do ERP em PostgreSQL, com infraestrutura como cÃ³digo, Kubernetes local e orquestraÃ§Ã£o no Airflow. A carga preservou setenta e seis mil, duzentas e seis linhas. A demonstraÃ§Ã£o usa capturas reais com cortes de tempo e narraÃ§Ã£o sintÃ©tica.

Tela: `.runtime/presentation/slide-1.png`.

## 00:22 a 01:00 — Arquitetura e estratÃ©gia

A origem Ã© o arquivo ZIP oficial da certificaÃ§Ã£o. Como ele representa uma exportaÃ§Ã£o completa, adotamos ingestÃ£o por snapshot, sem simular um CDC inexistente. Cada execuÃ§Ã£o congela sua prÃ³pria cÃ³pia e valida arquivos, cabeÃ§alhos, tipos e chaves. O Meltano executa a extraÃ§Ã£o e a carga com tap CSV e target Postgres, em pods separados. As tabelas chegam a um schema de staging exclusivo. Depois, a validaÃ§Ã£o compara todos os valores com a fonte. Somente entÃ£o uma transaÃ§Ã£o publica as sete tabelas e o marcador do snapshot.

Tela: `.runtime/presentation/slide-2.png`.

## 01:00 a 01:34 — Deploy real, reaplicaÃ§Ã£o

O ambiente executa no Ubuntu, dentro do WSL dois, usando o Docker Desktop. O script de deploy cria o cluster Kind, constrÃ³i as imagens e carrega os containers no nÃ³. O Terraform provisiona os recursos Kubernetes, e uma segunda etapa instala o chart oficial do Airflow. Esta saÃ­da Ã© uma reaplicaÃ§Ã£o real do deploy. As duas etapas terminaram sem alteraÃ§Ãµes, e todos os pods estavam prontos. Os volumes, credenciais e estados permanecem fora do repositÃ³rio, no diretÃ³rio privado do usuÃ¡rio Linux.

Tela: `evidence/deploy-screen.png`.

## 01:34 a 02:03 — Airflow em execuÃ§Ã£o

Aqui vemos a execuÃ§Ã£o certification video em andamento no Airflow. O sensor confirmou a presenÃ§a do ZIP, e a preparaÃ§Ã£o congelou a fonte. As cargas sÃ£o independentes, com atÃ© quatro tarefas em execuÃ§Ã£o ao mesmo tempo. Cada carga usa o Kubernetes Pod Operator para iniciar seu container Meltano. As dependÃªncias impedem validar antes de concluir todas as tabelas. O agendamento diÃ¡rio ocorre Ã s seis horas, no fuso de SÃ£o Paulo.

Tela: `evidence/airflow-running.png`.

## 02:03 a 02:33 — Airflow concluÃ­do

A mesma execuÃ§Ã£o chegou ao estado de sucesso em aproximadamente cinquenta segundos neste computador. As doze tarefas do fluxo principal concluÃ­ram, e o tratamento de falha ficou como skipped, porque nÃ£o houve erro. A publicaÃ§Ã£o sÃ³ comeÃ§ou depois da reconciliaÃ§Ã£o integral. Contagens e hashes ficam registrados no schema de auditoria. Esse tempo Ã© uma observaÃ§Ã£o do ambiente local, com imagens jÃ¡ disponÃ­veis, e nÃ£o uma garantia de desempenho em produÃ§Ã£o.

Tela: `evidence/airflow-video-success.png`.

## 02:33 a 03:06 — Dados no PostgreSQL

A consulta no destino mostra dez agÃªncias, novecentos e noventa e oito clientes, cem vÃ­nculos de colaboradores com agÃªncias, cem colaboradores, novecentas e noventa e nove contas, duas mil propostas de crÃ©dito e setenta e uma mil, novecentas e noventa e nove transaÃ§Ãµes. As contagens conferem com a origem, e os hashes de todos os valores tambÃ©m. Identificamos uma conta e quatro propostas que jÃ¡ referenciam cliente ausente na fonte. Preservamos essas linhas e registramos o aviso, sem inventar clientes para esconder o problema.

Tela: `evidence/verification-screen.png`.

## 03:06 a 03:41 — ResiliÃªncia comprovada

AlÃ©m da carga normal, testamos recuperaÃ§Ã£o e proteÃ§Ã£o dos dados. Uma falha transitÃ³ria em contas recuperou na segunda tentativa. Uma falha permanente terminou com a DAG e a auditoria em failed, mantendo o snapshot anterior. Um teste alterou um valor do staging e comprovou que a validaÃ§Ã£o bloqueia a publicaÃ§Ã£o. Outro provocou erro na Ãºltima tabela depois de operaÃ§Ãµes nas anteriores e comprovou rollback integral. Os sete testes de fonte e os cinco testes de banco passaram. Reprocessar o mesmo ZIP produziu zero diferenÃ§as nos dados.

Tela: `.runtime/presentation/slide-6.png`.

## 03:41 a 04:17 — SeguranÃ§a e limites

As senhas sÃ£o geradas uma vez e enviadas por Kubernetes Secrets. NÃ£o entram no cÃ³digo, nas imagens ou no estado do Terraform. Os pods de ingestÃ£o executam sem privilÃ©gios e sem token de service account. A conta do analista permite apenas leitura. Verificamos que ela nÃ£o consegue inserir dados nem criar objetos no schema raw. A interface e o banco usam acesso local por port forward. Para produÃ§Ã£o, ainda seriam necessÃ¡rios autenticaÃ§Ã£o corporativa, TLS, backup, retenÃ§Ã£o e uma infraestrutura com disponibilidade adequada.

Tela: `.runtime/presentation/slide-7.png`.

## 04:17 a 04:54 — ReproduÃ§Ã£o e entrega

O pacote inclui infraestrutura, configuraÃ§Ã£o Meltano, DAGs, SQL, testes e documentaÃ§Ã£o de operaÃ§Ã£o. O README apresenta os comandos para subir o ambiente, executar a carga e verificar os resultados. As views analytics oferecem uma base para indicadores de transaÃ§Ãµes, atividade de clientes e crÃ©dito. O prÃ³ximo trabalho de negÃ³cio Ã© definir mÃ©tricas e construir o dashboard. Um ranking causal de investimentos exige desenho estatÃ­stico adicional. A prova de conceito entrega a infraestrutura e o pipeline funcionando, com evidÃªncias verificÃ¡veis.

Tela: `.runtime/presentation/slide-8.png`.

Duração planejada: 294.0 segundos.

Na gravação, mantenha senhas e registros de clientes fora da tela. Mostre o status Success no Airflow e as contagens de todas as sete tabelas no destino. O deploy mostrado é uma reaplicação, com Terraform sem alterações.
