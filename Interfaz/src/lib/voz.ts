// Voice messages: record with the microphone and turn the recording into a small WAV
// (16 kHz, mono, 16-bit). Chrome records WebM/Opus, which Gemini doesn't accept, so we convert here.

const FRECUENCIA = 16000;

export interface Grabacion {
  parar: () => Promise<Blob>; // stops and returns the WAV
  cancelar: () => void;
}

export function vozDisponible(): boolean {
  return typeof window !== "undefined" && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined";
}

// Asks for the microphone (the browser shows its own permission prompt) and starts recording.
export async function empezarGrabacion(): Promise<Grabacion> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const grabadora = new MediaRecorder(stream);
  const trozos: Blob[] = [];
  grabadora.ondataavailable = (e) => {
    if (e.data.size > 0) trozos.push(e.data);
  };
  grabadora.start();
  const soltarMicro = () => stream.getTracks().forEach((t) => t.stop());

  return {
    parar: () =>
      new Promise<Blob>((resolve, reject) => {
        grabadora.onstop = async () => {
          soltarMicro();
          try {
            resolve(await aWav(new Blob(trozos, { type: grabadora.mimeType })));
          } catch (e) {
            reject(e);
          }
        };
        grabadora.stop();
      }),
    cancelar: () => {
      grabadora.onstop = null;
      if (grabadora.state !== "inactive") grabadora.stop();
      soltarMicro();
    },
  };
}

// Any recording the browser can decode -> mono 16 kHz WAV.
export async function aWav(grabado: Blob): Promise<Blob> {
  const contexto = new AudioContext();
  const original = await contexto.decodeAudioData(await grabado.arrayBuffer());
  void contexto.close();
  const muestras = Math.max(1, Math.ceil(original.duration * FRECUENCIA));
  const offline = new OfflineAudioContext(1, muestras, FRECUENCIA); // 1 channel: downmixes and resamples
  const fuente = offline.createBufferSource();
  fuente.buffer = original;
  fuente.connect(offline.destination);
  fuente.start();
  const audio = (await offline.startRendering()).getChannelData(0);
  return new Blob([cabeceraWav(audio.length), pcm16(audio)], { type: "audio/wav" });
}

function pcm16(audio: Float32Array): ArrayBuffer {
  const datos = new DataView(new ArrayBuffer(audio.length * 2));
  audio.forEach((m, i) => datos.setInt16(i * 2, Math.max(-1, Math.min(1, m)) * 0x7fff, true));
  return datos.buffer;
}

function cabeceraWav(muestras: number): ArrayBuffer {
  const v = new DataView(new ArrayBuffer(44));
  const texto = (pos: number, s: string) => [...s].forEach((c, i) => v.setUint8(pos + i, c.charCodeAt(0)));
  texto(0, "RIFF");
  v.setUint32(4, 36 + muestras * 2, true);
  texto(8, "WAVE");
  texto(12, "fmt ");
  v.setUint32(16, 16, true); // fmt chunk size
  v.setUint16(20, 1, true); // PCM
  v.setUint16(22, 1, true); // mono
  v.setUint32(24, FRECUENCIA, true);
  v.setUint32(28, FRECUENCIA * 2, true); // bytes per second
  v.setUint16(32, 2, true); // block align
  v.setUint16(34, 16, true); // bits per sample
  texto(36, "data");
  v.setUint32(40, muestras * 2, true);
  return v.buffer;
}
