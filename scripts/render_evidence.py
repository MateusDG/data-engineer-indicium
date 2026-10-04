"""Present actual captured command output for the technical demonstration."""
import html
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
evidence = root / "evidence"
styles = """
body{margin:0;background:#102638;color:#eaf3f7;font:24px Arial;padding:48px 64px}
h1{font-size:40px;margin:0 0 16px}p{color:#a5c7ce;margin:0 0 32px}
pre{font:22px/1.6 Consolas,monospace;margin:0;white-space:pre-wrap}a{color:#74d5c5}
"""
def page(filename, title, command, output):
    (evidence / filename).write_text(f'<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>{title}</title>'
        f'<style>{styles}</style><h1>{html.escape(title)}</h1><p>Saída real do terminal, recorte para apresentação. 04/10/2026.</p>'
        f'<pre style="color:#74d5c5">$ {html.escape(command)}</pre><br><pre>{html.escape(output)}</pre></html>', encoding='utf-8')

deploy = re.sub(r'\x1b\[[0-9;]*m', '', (evidence / 'deploy.txt').read_text())
selected = [line for line in deploy.splitlines() if 'No changes.' in line or 'Apply complete!' in line
            or 'Secrets configured.' in line or 'partitioned roll out complete' in line]
pod_table = deploy[deploy.rfind('NAME '):].split('Ambiente pronto.')[0].strip()
page('deploy.html','Deploy reproduzível no Kubernetes','bash scripts/deploy.sh',
     '\n'.join(selected) + '\n\n' + pod_table)
verification = '\n'.join(line.rstrip() for line in (evidence / 'verification.txt').read_text().splitlines())
counts = verification.split('(7 rows)')[0] + '(7 rows)'
page('verification.html','Verificação no PostgreSQL','bash scripts/verify.sh',counts)
print('Created presentation views from captured output.')
