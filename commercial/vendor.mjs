import {mkdir, copyFile} from 'node:fs/promises';
await mkdir(new URL('static/vendor/', import.meta.url), {recursive:true});
for (const [source, target] of [['dist/echarts.min.js','echarts.min.js'],['LICENSE','ECHARTS-LICENSE.txt'],['NOTICE','ECHARTS-NOTICE.txt']]) {
  await copyFile(new URL('node_modules/echarts/' + source, import.meta.url), new URL('static/vendor/' + target, import.meta.url));
}
