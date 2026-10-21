// Send a consistent PCM WAV instead of browser-specific WebM/MP4 codecs.
export const MAX_RECORDING_MS = 25_000;
export const MAX_AUDIO_BYTES = 25 * 1024 * 1024;

export function encodeWav(samples: Float32Array, sampleRate = 16000): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const write = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i));
  };
  write(0, 'RIFF'); view.setUint32(4, buffer.byteLength - 8, true);
  write(8, 'WAVE'); write(12, 'fmt '); view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  write(36, 'data'); view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const value = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, value < 0 ? value * 32768 : value * 32767, true);
  }
  return new Blob([buffer], { type: 'audio/wav' });
}

export async function recordingToWav(blob: Blob): Promise<Blob> {
  if (!blob.size) throw new Error('No audio was recorded. Please speak for a few seconds and try again.');
  if (blob.size > MAX_AUDIO_BYTES) throw new Error('This recording is too large. Please record a shorter message.');
  const context = new AudioContext();
  try {
    const decoded = await context.decodeAudioData(await blob.arrayBuffer());
    if (!decoded.length) throw new Error('The recording is empty. Please try again.');
    const offline = new OfflineAudioContext(1, Math.ceil(decoded.duration * 16000), 16000);
    const source = offline.createBufferSource();
    source.buffer = decoded;
    source.connect(offline.destination);
    source.start();
    const mono = await offline.startRendering();
    return encodeWav(mono.getChannelData(0));
  } finally {
    await context.close();
  }
}

export function microphoneError(error: unknown): string {
  const name = error instanceof Error ? error.name : '';
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'Microphone access is blocked. Allow the microphone for this site in your browser settings, then try again.';
  if (name === 'NotFoundError') return 'No microphone was found. Connect a microphone and try again.';
  if (name === 'NotReadableError') return 'Your microphone is unavailable. Close other apps using it, then try again.';
  if (name === 'NotSupportedError') return 'This browser could not read the recording. Please try Chrome or Safari.';
  return error instanceof Error ? error.message : 'Recording failed. Please try again.';
}
