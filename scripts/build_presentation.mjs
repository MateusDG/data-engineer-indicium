// Run with the Codex artifact runtime. See docs/APRESENTACAO.md.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation, PresentationFile} from '@oai/artifact-tool';

const {SKILL_DIR, TMP_DIR, WORKSPACE_DIR, RUNTIME_PYTHON, FINAL_PPTX} = process.env;
const {resolvePresentationFont, finalizePresentation} = await import(pathToFileURL(
  path.join(SKILL_DIR, 'container_tools/artifact_tool_utils.mjs')).href);
const family = resolvePresentationFont();
const fontPolicy = {basis:'design', families:[family]};
const p = Presentation.create({slideSize:{width:1280,height:720}});
const colors = {navy:'#102638', green:'#087F78', ink:'#17364B', muted:'#526677', paper:'#F6F8FA', white:'#FFFFFF'};
function text(s,t,x,y,w,h,size=28,bold=false,color=colors.ink){
  const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  sh.text=t; sh.text.style={typeface:family,fontSize:size,bold,color,autoFit:'none'}; return sh;
}
function slide(title){ const s=p.slides.add(); s.background.fill=colors.paper; text(s,title,64,40,1152,90,44,true); return s; }
function notes(s,t){ s.speakerNotes.textFrame.setText(t); }
function table(s,values,x,y,w,h,widths){
  const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
  t.borders.assign({fill:'#D4DEE4',width:1,style:'solid'});
  for(let r=0;r<values.length;r++) for(let c=0;c<values[0].length;c++){
    const cell=t.getCell(r,c); cell.fill=r===0?colors.navy:r===values.length-1?'#DEEFEC':r%2?'#FFFFFF':'#EEF3F6';
    cell.text.style={typeface:family,fontSize:25,color:r===0?colors.white:colors.ink,bold:r===0||r===values.length-1,autoFit:'none'};
  }
  return t;
}

let s=p.slides.add(); s.background.fill=colors.navy;
text(s,'BanVic',64,62,1100,80,40,true,'#74D5C5');
text(s,'Ingestão de dados\ndo ERP',64,178,1136,190,68,true,colors.white);
text(s,'POC executada em Kubernetes local',64,406,1100,55,32,false,'#D4E5EC');
text(s,'7 tabelas',64,525,315,65,44,true,colors.white);
text(s,'76.206 linhas',449,525,365,65,44,true,colors.white);
text(s,'12 testes',879,525,315,65,44,true,colors.white);
text(s,'Engenharia de Dados  /  Outubro de 2026',64,634,1100,45,24,false,'#D4E5EC');
notes(s,'Projeto de certificação BanVic. Fonte oficial Dados Banvic.zip, SHA256 646aada76645cab694741fa730d9792b40840c41823abb60bd7547a2038ba790. Evidências: evidence/warehouse.json. 7 testes de fonte e 5 testes de banco aprovados.');

s=slide('A publicação só ocorre após a reconciliação');
text(s,'Terraform provisiona o namespace, volumes e PostgreSQL. Helm instala o Airflow.',64,138,1152,72,28);
const labels=['ZIP oficial','Snapshot\nimutável','Meltano\n7 cargas','Staging por\nexecução','Validação\nintegral','Publicação\natômica'];
const boxes=labels.map((t,i)=>{ const b=s.shapes.add({geometry:'rect',position:{left:64+i*194,top:271,width:170,height:100},fill:i===5?colors.green:colors.navy,line:{fill:'none',width:0}}); b.text=t; b.text.style={typeface:family,fontSize:27,bold:true,color:colors.white,autoFit:'none',alignment:'center'}; return b; });
for(let i=0;i<boxes.length-1;i++) s.shapes.connect(boxes[i],boxes[i+1],{kind:'straight',fromSide:'right',toSide:'left',line:{fill:colors.green,width:3},tail:{type:'arrow',width:'med',length:'med'}});
text(s,'Airflow coordena as dependências e as tentativas de cada tarefa.',64,410,1152,50,28);
text(s,'raw',64,509,300,55,32,true,colors.green); text(s,'Valores de origem',64,566,300,60,26);
text(s,'audit',458,509,300,55,32,true,colors.green); text(s,'Execuções e hashes',458,566,300,60,26);
text(s,'analytics',852,509,340,55,32,true,colors.green); text(s,'Views para analistas',852,566,340,60,26);
notes(s,'Diagrama editável. Arquitetura implementada em infra/, pipeline/, dags/ e sql/. LocalExecutor com KubernetesPodOperator. Snapshot completo sem CDC. Referências: https://airflow.apache.org/docs/apache-airflow-providers-cncf-kubernetes/stable/operators.html e https://docs.meltano.com/reference/command-line-interface/#run');

s=slide('O deploy reaproveita a infraestrutura');
text(s,'Execução no Ubuntu / WSL 2 com Docker integrado',64,136,1152,54,28);
text(s,'bash scripts/deploy.sh\nbash scripts/access.sh',64,224,1152,105,35,true,colors.green);
text(s,'Terraform: No changes.\n0 added, 0 changed, 0 destroyed.',64,365,680,115,32,true);
text(s,'Kind  +  Terraform  +  Helm',64,549,1152,55,30,true);
text(s,'Credenciais e estado ficam fora do repositório.',64,612,1152,48,26,false,colors.muted);
notes(s,'Comandos executados de fato. O redeploy completo terminou com ausência de alterações nas duas etapas Terraform. Transcript público: evidence/deploy.txt. Os diretórios de dados e credenciais ficam em ~/banvic-local. A criação inicial usa 14 recursos Kubernetes e uma release Helm.');

s=slide('A DAG concluiu a carga em 49 segundos');
const shot=await fs.readFile(path.join(WORKSPACE_DIR,'evidence/airflow-success-overview.png'));
s.images.add({blob:new Uint8Array(shot),contentType:'image/png',alt:'Airflow real: certification_demo em Success, tarefas de carga e publicação verdes',fit:'contain',position:{left:64,top:148,width:850,height:530}});
text(s,'12 tarefas\ncom sucesso',962,213,260,130,32,true,colors.green);
text(s,'1 tratamento\nde falha skipped',962,381,260,120,26);
text(s,'Todas passaram\nna primeira tentativa.',962,550,260,110,26);
notes(s,'Captura real da execução certification_demo no Airflow 3.2.2. Duração exata 49.023 s. 12 tarefas com sucesso, record_failure skipped, todas as tarefas executadas com try_number 1. Não é benchmark nem promessa de desempenho. Evidências: evidence/certification_demo-tasks.json e evidence/airflow-success-overview.png.');

s=slide('As sete tabelas preservam 76.206 linhas');
const counts=[['Tabela','Origem','Destino'],['agencias','10','10'],['clientes','998','998'],['colaborador_agencia','100','100'],['colaboradores','100','100'],['contas','999','999'],['propostas_credito','2.000','2.000'],['transacoes','71.999','71.999'],['Total','76.206','76.206']];
table(s,counts,64,148,1152,415,[642,255,255]);
text(s,'Hashes de todos os valores também conferem.',64,593,1152,50,29,true,colors.green);
text(s,'A origem contém 5 vínculos com cliente ausente. O pipeline preserva e sinaliza esses registros.',64,652,1152,52,24,false,colors.muted);
notes(s,'Contagens medidas no ZIP e no PostgreSQL. Digest SHA256 calculado sobre todos os valores, independente da ordem. A origem contém 1 conta e 4 propostas com cliente ausente. Evidência: evidence/warehouse.json. Total 10+998+100+100+999+2000+71999=76206.');

s=slide('Os testes comprovam recuperação e rollback');
table(s,[['Cenário','Resultado verificado'],['Falha transitória em contas','Sucesso na segunda tentativa'],['Falha permanente em contas','DAG failed e snapshot anterior preservado'],['Alteração no staging','Validação bloqueia a publicação'],['Erro durante a publicação','Rollback das tabelas e do marcador']],64,158,1152,345,[510,642]);
text(s,'7 testes de fonte e 5 testes de banco aprovados.',64,548,1152,57,31,true,colors.green);
text(s,'Reprocessar o mesmo ZIP produziu zero diferenças nos dados.',64,616,1152,62,28);
notes(s,'Testes executados em 4/10/2026. certification_retry: load_contas try_number 2. certification_failure: load_contas failed try_number 3, record_failure success, pipeline_complete upstream_failed. Snapshot permaneceu certification_retry. Testes de banco fazem rollback dentro de SAVEPOINT para não alterar dados publicados. Evidências: warehouse-after-failure.json e JSONs de tarefas. A auditoria mantém também a execução de desenvolvimento inicialmente malsucedida.');

s=slide('O acesso dos analistas permite apenas leitura');
text(s,'Credenciais',64,160,340,55,32,true,colors.green);
text(s,'Kubernetes Secrets. Senhas aleatórias fora de Git, imagens e estado Terraform.',64,224,520,135,28);
text(s,'Execução',676,160,520,55,32,true,colors.green);
text(s,'Pods sem privilégios. Token de service account desativado nos pods de ingestão.',676,224,520,135,28);
text(s,'Consumo',64,411,520,55,32,true,colors.green);
text(s,'Usuário banvic_analyst com SELECT. Sem INSERT e sem CREATE no schema raw.',64,478,520,140,28);
text(s,'Limites da POC',676,411,520,55,32,true,colors.green);
text(s,'Um nó local. Autenticação de teste. Produção exige SSO, TLS, backup e retenção.',676,478,520,150,28);
notes(s,'Permissões verificadas por has_table_privilege e has_schema_privilege. Endpoints acessíveis por port-forward apenas em 127.0.0.1. Não há NetworkPolicy implementada no CNI padrão Kind. SimpleAuthManager apenas para ambiente local: https://airflow.apache.org/docs/apache-airflow/3.2.2/core-concepts/auth-manager/simple/index.html');

s=slide('O projeto está pronto para reprodução local');
text(s,'README com execução passo a passo',64,175,1152,58,34,true,colors.green);
text(s,'Infraestrutura, conectores, DAGs, SQL e testes no pacote de código.',64,250,1152,90,30);
text(s,'bash scripts/run_pipeline.sh\nbash scripts/verify.sh\nbash scripts/test.sh --integration',64,384,1152,164,32,true);
text(s,'Próxima etapa: definir métricas comerciais e construir o dashboard sobre analytics.',64,602,1152,75,28,false,colors.muted);
notes(s,'O desafio de engenharia entrega infraestrutura, ingestão e orquestração. Dashboard completo e ranking causal de investimentos são trabalhos posteriores. Correlações não garantem retorno financeiro. A entrega inclui apresentação e vídeo com capturas reais e cortes de tempo.');

await fs.mkdir(TMP_DIR,{recursive:true});
await fs.mkdir(path.dirname(FINAL_PPTX),{recursive:true});
const candidatePath=path.join(TMP_DIR,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidatePath);
await finalizePresentation({workspaceDir:WORKSPACE_DIR,candidatePath,finalPath:FINAL_PPTX,
  pythonExecutable:RUNTIME_PYTHON,
  integrityValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',
    '--require-native-table-slide','5','--require-native-table-slide','6'],
  requiredNativeTableOwnerSlides:[5,6], requiredNativeChartOwnerSlides:[], fontPolicy,
  verifyArtifactToolImport:true,receiptPath:path.join(TMP_DIR,`${path.basename(FINAL_PPTX)}.validation.json`)});
for(let i=0;i<p.slides.items.length;i++){
  const image=await p.export({slide:p.slides.items[i],format:'png',scale:1.5});
  await fs.writeFile(path.join(TMP_DIR,`slide-${i+1}.png`),new Uint8Array(await image.arrayBuffer()));
}
console.log(JSON.stringify({pptx:FINAL_PPTX,slides:p.slides.items.length,font:family}));
