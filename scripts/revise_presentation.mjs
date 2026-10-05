// Revises the existing engineering deck with current public review evidence.
// Runtime and execution instructions: docs/APRESENTACAO.md.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {FileBlob, PresentationFile} from '@oai/artifact-tool';

const {SKILL_DIR, TMP_DIR, WORKSPACE_DIR, RUNTIME_PYTHON, FINAL_PPTX, SOURCE_PPTX} = process.env;
for (const [name, value] of Object.entries({SKILL_DIR, TMP_DIR, WORKSPACE_DIR, RUNTIME_PYTHON, FINAL_PPTX, SOURCE_PPTX})) {
  if (!path.isAbsolute(value ?? '')) throw new Error(`Set absolute ${name}`);
}
const {resolvePresentationFont, finalizePresentation} = await import(pathToFileURL(
  path.join(SKILL_DIR, 'container_tools/artifact_tool_utils.mjs')).href);
const family = resolvePresentationFont();
const sourceSha = createHash('sha256').update(await fs.readFile(SOURCE_PPTX)).digest('hex');
const p = await PresentationFile.importPptx(await FileBlob.load(SOURCE_PPTX));
if (p.slides.items.length !== 8) throw new Error('Expected the original eight-slide deck');
const snapshot = await p.inspect({kind:'textbox', maxChars:100000});
const records = snapshot.ndjson.split('\n').filter(Boolean).map(line => JSON.parse(line));
function replace(before, after) {
  const matches = records.filter(record => record.kind === 'textbox' && record.text === before);
  if (matches.length !== 1) throw new Error(`Expected exactly one text anchor: ${before}`);
  const target=p.resolve(matches[0].id);
  if (before.includes('\n')) target.text=after;
  else target.text.replace(before, after);
  return target;
}
const finalRun = JSON.parse(await fs.readFile(path.join(WORKSPACE_DIR, 'evidence/review3/review3_20261005_final.json'), 'utf8'));
if (finalRun.state !== 'success') throw new Error('Final ingestion is not successful');
const duration = (Date.parse(finalRun.end_date) - Date.parse(finalRun.start_date)) / 1000;
replace('12 testes', '30 testes');
const deployText=replace('bash scripts/deploy.sh\nbash scripts/access.sh', 'bash scripts/deploy.sh\nbash scripts/access.sh\nbash scripts/run_pipeline.sh');
deployText.position={left:64,top:224,width:1152,height:135};
replace('A DAG concluiu a carga em 49 segundos', 'Airflow coordena sete cargas e publicação');
replace('Todas passaram\nna primeira tentativa.', '05/10: 55,826 s\nSem retries na\ncarga final.');
replace('7 testes de fonte e 5 testes de banco aprovados.', '30 testes de fonte, banco, entrega e análise aprovados.');
replace('Próxima etapa: definir métricas comerciais e construir o dashboard sobre analytics.', 'Dashboard comercial implantado. Impacto de investimentos requer dados de intervenção.');
const colors = {navy:'#102638', green:'#087F78', ink:'#17364B', muted:'#526677', paper:'#F6F8FA', white:'#FFFFFF'};
function text(slide, value, x, y, w, h, size=28, bold=false, color=colors.ink) {
  const shape=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  shape.text=value;
  shape.text.style={typeface:family,fontSize:size,bold,color,autoFit:'none'};
}
function slide(title) {
  const item=p.slides.add(); item.background.fill=colors.paper;
  text(item,title,64,40,1152,90,44,true);
  return item;
}
function table(item, values, y, h, widths) {
  const t=item.tables.add({rows:values.length,columns:values[0].length,left:64,top:y,width:1152,height:h,columnWidths:widths,values});
  t.borders.assign({fill:'#D4DEE4',width:1,style:'solid'});
  for(let r=0;r<values.length;r++) for(let c=0;c<values[0].length;c++) {
    const cell=t.getCell(r,c); cell.fill=r===0?colors.navy:r%2?colors.white:'#EEF3F6';
    cell.text.style={typeface:family,fontSize:25,color:r===0?colors.white:colors.ink,bold:r===0,autoFit:'none'};
  }
}
text(p.slides.items[3],'Interface demonstrada em 04/10; nova carga verificada em 05/10.',64,677,850,29,18,false,colors.muted);
p.slides.items[0].speakerNotes.textFrame.setText('Revisão de 05/10/2026. Sete tabelas e 76.206 linhas integralmente reconciliadas. 7 testes de fonte, 3 de entrega, 5 de banco e 15 comerciais aprovados. Evidências: evidence/review3/ e evidence/commercial/.');
p.slides.items[2].speakerNotes.textFrame.setText('Sequência inicial: deploy da engenharia, acesso local e primeira ingestão. Somente depois da publicação, executar bash scripts/deploy_commercial.sh e bash scripts/access.sh para instalar e acessar o dashboard. Deploys executados previamente pelos scripts entregues. Nesta revisão, os três módulos Terraform passaram por validate e plan sem alterações. Evidência atual: evidence/review3/terraform.json; deploy anterior: evidence/deploy.txt e evidence/review/redeploy-clean-package.txt.');
p.slides.items[3].speakerNotes.textFrame.setText(`A imagem preserva a captura real anterior de certification_demo, em 04/10, com 49,023 s, para manter a legibilidade da interface. A revisão atual executou ${finalRun.run_id} em 05/10: duração ${duration.toFixed(3)} s, 12 tarefas success, record_failure skipped, todas na primeira tentativa. A nova execução foi conferida pela API e no navegador, com captura em evidence/review3/airflow-final-success.png. As medidas pertencem às respectivas execuções; não são promessa de desempenho. Evidência atual: evidence/review3/${finalRun.run_id}.json.`);
p.slides.items[5].speakerNotes.textFrame.setText('Cenários repetidos em 05/10/2026: retry em contas, falha permanente, sensor com fonte ausente, ZIP inválido e execução final bem-sucedida. A falha permanente e a fonte inválida preservaram todas as tabelas e o marcador anterior. Os testes de banco validaram adulteração de staging e rollback com SAVEPOINT. Trinta testes passaram; dez grupos HTTP também foram verificados. Evidências: evidence/review3/ e evidence/commercial/api-validation.json.');
p.slides.items[7].speakerNotes.textFrame.setText('O README documenta infraestrutura, ingestão, dashboard e testes. Pacote de código separado do PPTX e sem fonte oficial ou segredos. A revisão atual excluiu gravação, edição, geração e verificação de vídeo, por solicitação do usuário. A certificação ainda lista vídeo como um entregável. O ranking causal de investimentos permanece não identificado pela fonte disponível.');

let s=slide('A carteira é acompanhada em seis áreas');
text(s,'Referência histórica: outubro a dezembro de 2022',64,137,1152,50,28,false,colors.muted);
table(s,[['Indicador','Resultado do trimestre'],['Transações','28.532'],['Clientes ativos / elegíveis','700 / 998'],['Transações por cliente ativo','40,76'],['Continuidade de atividade','427 de 467  ·  91,4%']],211,320,[680,472]);
text(s,'Visão executiva, atividade, rede, crédito, alavancas e qualidade.',64,570,1152,52,28,true,colors.green);
text(s,'Dezembro concentra 25.319 transações. Causa não registrada; inatividade não confirma churn.',64,636,1152,66,25,false,colors.muted);
s.speakerNotes.textFrame.setText('Dashboard real em http://localhost:8090, autenticado e ligado ao PostgreSQL somente leitura. Filtros de período, canal e agência, coortes, exportação e critérios de qualidade. Valores conferidos pela API. Fontes: docs/RESULTADOS_COMERCIAIS.md; evidence/commercial/dashboard-default.json. A base é histórica, até janeiro/2023, e não descreve a situação de 2026.');

s=slide('Prioridades de validação, com incerteza');
text(s,'Diferença ajustada em transações por cliente/mês — 2022-Q4',64,137,1152,50,28,false,colors.muted);
table(s,[['Prioridade exploratória','Diferença','IC individual 95%'],['1  Uso do cartão de crédito','+1,13','−0,01 a +2,27'],['2  Uso do Pix','+0,92','−0,16 a +2,00'],['3  Três ou mais modalidades','+0,40','−0,83 a +1,62']],211,264,[580,205,367]);
text(s,'Nenhum efeito causal de investimento foi identificado.',64,513,1152,57,31,true,colors.green);
text(s,'A ordem orienta pilotos. Faltam intervenção, grupo comparável, custos e margem para medir impacto e ROI.',64,586,1152,99,28,false,colors.muted);
s.speakerNotes.textFrame.setText('Estimador AIPW com cinco folds e ajuste temporal anterior à exposição, 888 clientes elegíveis. Ranking de validação ordenado pelo limite inferior do IC simultâneo, com regras de comparabilidade e estabilidade; a tabela mostra ICs individuais. Todos os três ICs de frequência incluem zero. Canal digital não foi ranqueado por sobreposição/balanceamento insuficientes. Holm mantém família de oito testes; ICs simultâneos e diagnósticos estão no dashboard. Sem registro de ação comercial e confundidores adequados, significância ou balanceamento não identificam causalidade. O planejador retorna 321 por grupo para +20% em transações com 955 elegíveis históricos; isso não define elegibilidade atual nem garante retorno. Fontes: docs/METODOLOGIA_CAUSAL.md; evidence/commercial/ranking.json.');

await fs.mkdir(TMP_DIR,{recursive:true});
await fs.mkdir(path.dirname(FINAL_PPTX),{recursive:true});
const candidate=path.join(TMP_DIR,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
await finalizePresentation({workspaceDir:WORKSPACE_DIR,candidatePath:candidate,finalPath:FINAL_PPTX,
  pythonExecutable:RUNTIME_PYTHON,
  integrityValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',
    ...[5,6,9,10].flatMap(n=>['--require-native-table-slide',String(n)])],
  requiredNativeTableOwnerSlides:[5,6,9,10],requiredNativeChartOwnerSlides:[],
  fontPolicy:{basis:'reference',families:[family],referencePath:SOURCE_PPTX,referenceSha256:sourceSha},
  verifyArtifactToolImport:true,receiptPath:path.join(TMP_DIR,'validation.json')});
const finalDeck=await PresentationFile.importPptx(await FileBlob.load(FINAL_PPTX));
for(let i=0;i<finalDeck.slides.items.length;i++) {
  const preview=await finalDeck.export({slide:finalDeck.slides.items[i],format:'png',scale:1.5});
  await fs.writeFile(path.join(TMP_DIR,`slide-${i+1}.png`),new Uint8Array(await preview.arrayBuffer()));
}
console.log(JSON.stringify({pptx:FINAL_PPTX,slides:finalDeck.slides.items.length,source_sha256:sourceSha}));
