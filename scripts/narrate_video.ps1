# Local Portuguese narration. No external account or media service is used.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$banvicRoot = Split-Path $PSScriptRoot -Parent
$banvicAudio = Join-Path $banvicRoot '.runtime/video'
New-Item -ItemType Directory -Force $banvicAudio | Out-Null
$banvicScenes = Get-Content (Join-Path $banvicRoot 'docs/video_scenes.json') -Raw -Encoding utf8 | ConvertFrom-Json
$banvicSpeaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
    $banvicSpeaker.SelectVoice('Microsoft Maria Desktop')
    $banvicSpeaker.Rate = 3
    for ($banvicIndex = 0; $banvicIndex -lt $banvicScenes.Count; $banvicIndex++) {
        $banvicWave = Join-Path $banvicAudio ('audio-{0}.wav' -f ($banvicIndex + 1))
        $banvicSpeaker.SetOutputToWaveFile($banvicWave)
        $banvicSpeaker.Speak($banvicScenes[$banvicIndex].speech)
        $banvicSpeaker.SetOutputToNull()
    }
} finally {
    $banvicSpeaker.Dispose()
}
Write-Output 'Nine narration segments generated locally.'
