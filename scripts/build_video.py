"""Assemble the narrated technical demonstration from verified slides and real captures.

Run in WSL after narrate_video.ps1, with ffmpeg/ffprobe installed.
The video is an edited presentation with actual evidence, not continuous screen recording.
"""
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
work = root / '.runtime/video'
work.mkdir(exist_ok=True)
scenes = json.loads((root / 'docs/video_scenes.json').read_text(encoding='utf-8'))
font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
total = 0
segments = []
durations = [float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration',
             '-of','default=noprint_wrappers=1:nokey=1',str(work/f'audio-{i}.wav')])) + 1.0
             for i in range(1,len(scenes)+1)]
if not 180 <= sum(durations) <= 300:
    raise ValueError(f'Video duration outside the challenge requirement: {sum(durations):.1f}s')
for index, scene in enumerate(scenes, 1):
    audio = work / f'audio-{index}.wav'
    duration = durations[index-1]
    total += duration
    (work / f'label-{index}.txt').write_text(scene['title'] + '  /  Capturas reais com cortes de tempo', encoding='utf-8')
    target = work / f'segment-{index}.mp4'
    label = f'.runtime/video/label-{index}.txt'
    filters = (f'scale=1920:1000:force_original_aspect_ratio=decrease,'
               f'pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x102638,'
               f'drawbox=x=0:y=1030:w=iw:h=50:color=0x102638:t=fill,'
               f'drawtext=fontfile={font}:textfile={label}:fontcolor=white:fontsize=24:x=64:y=1042')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-framerate','24',
                    '-i',str(root/scene['image']),'-i',str(audio),'-vf',filters,'-af','apad=pad_dur=1',
                    '-t',f'{duration:.3f}','-c:v','libx264','-preset','veryfast','-crf','22',
                    '-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(target)],
                   cwd=root,check=True)
    segments.append(target)
    print(f'Encoded scene {index}/9: {duration:.1f}s', flush=True)
if not 180 <= total <= 300:
    raise ValueError(f'Video duration outside the challenge requirement: {total:.1f}s')
playlist = work / 'concat.txt'
playlist.write_text('\n'.join(f"file '{path.as_posix()}'" for path in segments) + '\n')
output = root/'delivery/BanVic-Demonstracao.mp4'
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(playlist),
                '-c','copy','-movflags','+faststart',str(output)],check=True)
receipt = {'duration_seconds':round(total,3),'resolution':'1920x1080','fps':24,'scenes':len(scenes),
           'voice':'Microsoft Maria Desktop, pt-BR, generated locally',
           'format':'Narrated presentation with real screenshots and time cuts'}
(root/'evidence/video.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(receipt),flush=True)
