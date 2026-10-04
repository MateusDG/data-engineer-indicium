# Apresentação e vídeo

## Arquivos

- `delivery/BanVic-Apresentacao-Final.pptx`: oito slides com texto, diagrama e tabelas editáveis. A captura do Airflow permanece como imagem real.
- `delivery/BanVic-Demonstracao.mp4`: vídeo narrado em português, com capturas reais, cortes de tempo e slides explicativos.
- `docs/ROTEIRO_VIDEO.md`: texto completo e marcações de tempo para revisão ou gravação com a voz do autor.

O vídeo usa voz sintética local Microsoft Maria, sem clonagem de voz ou envio de conteúdo a serviço de mídia externo. Ele apresenta uma reaplicação real do deploy, a mesma execução Airflow em andamento e concluída, e a consulta real das contagens no PostgreSQL. Os recortes do terminal identificam sua origem. Não se apresenta uma montagem como gravação contínua da tela.

## Revisão realizada

A apresentação passou pelos validadores de integridade do arquivo, geometria, fontes e presença de tabelas nativas. Os oito slides foram renderizados a partir do PPTX final e revisados visualmente. O diagrama usa conectores e formas editáveis. As duas tabelas são objetos nativos do PowerPoint. Nenhum gráfico quantitativo foi necessário.

Não foi realizado teste de edição dentro do Microsoft PowerPoint ou do Google Slides. A verificação confirma a estrutura do PPTX e sua renderização no runtime de artefatos, sem afirmar comportamento idêntico em todo aplicativo.

## Reproduzir os materiais

O pipeline não depende das ferramentas de apresentação. Para reconstruir os slides, `scripts/build_presentation.mjs` usa o runtime de artefatos e os validadores da habilidade Presentations do Codex. Defina os caminhos absolutos `SKILL_DIR`, `RUNTIME_NODE_MODULES`, `RUNTIME_PYTHON`, `WORKSPACE_DIR`, `TMP_DIR` e `FINAL_PPTX`, seguindo a configuração do runtime disponível no seu computador. Use um novo nome de saída a cada revisão.

Para reconstruir somente a narração e o vídeo, são necessários os PNGs revisados, as capturas em `evidence/`, Windows com a voz Microsoft Maria Desktop e ffmpeg/ffprobe no Ubuntu:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/narrate_video.ps1
```

No Ubuntu:

```bash
python3 scripts/build_video.py
```

O script verifica a duração antes de renderizar e exige um vídeo entre três e cinco minutos. Os materiais intermediários ficam em `.runtime/` e não entram no pacote de código.

## Entregar

Revise o vídeo e confirme as regras da plataforma de certificação. O ZIP de código exclui a fonte oficial, segredos e estado local. Envie o ZIP ou disponibilize o código em um repositório Git conforme a opção da plataforma. O vídeo e o PPTX ficam separados. Este projeto não publica arquivos nem envia a inscrição automaticamente.
