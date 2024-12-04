class Recorder {
    constructor(stream) {
        this.sampleBits = 16;
        this.inputSampleRate = 48000;
        this.outputSampleRate = 16000;
        this.channelCount = 1;
        this.context = new AudioContext();
        this.audioInput = this.context.createMediaStreamSource(stream);
        this.recorder = this.context.createScriptProcessor(4096, this.channelCount, this.channelCount);
        this.audioData = {
            size: 0,
            buffer: [],
            inputSampleRate: this.inputSampleRate,
            inputSampleBits: this.sampleBits,
            clear() {
                this.buffer = [];
                this.size = 0;
            },
            input(data) {
                this.buffer.push(new Float32Array(data));
                this.size += data.length;
            },
            encodePCM() {
                const bytes = new Float32Array(this.size);
                let offset = 0;
                for (let i = 0; i < this.buffer.length; i++) {
                    bytes.set(this.buffer[i], offset);
                    offset += this.buffer[i].length;
                }
                const dataLength = bytes.length * (this.inputSampleBits / 8);
                const buffer = new ArrayBuffer(dataLength);
                const data = new DataView(buffer);
                offset = 0;
                for (let i = 0; i < bytes.length; i++, offset += 2) {
                    const s = Math.max(-1, Math.min(1, bytes[i]));
                    data.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
                }
                return new Blob([data], { type: 'audio/pcm' });
            }
        };

        this.recorder.onaudioprocess = (e) => {
            const resampledData = this.downsampleBuffer(
                e.inputBuffer.getChannelData(0),
                this.inputSampleRate,
                this.outputSampleRate
            );
            this.audioData.input(resampledData);
        };
    }

    start() {
        this.audioInput.connect(this.recorder);
        this.recorder.connect(this.context.destination);
    }

    stop() {
        this.recorder.disconnect();
    }

    getBlob() {
        return this.audioData.encodePCM();
    }

    clear() {
        this.audioData.clear();
    }

    downsampleBuffer(buffer, inputSampleRate, outputSampleRate) {
        if (outputSampleRate === inputSampleRate) {
            return buffer;
        }
        const sampleRateRatio = inputSampleRate / outputSampleRate;
        const newLength = Math.round(buffer.length / sampleRateRatio);
        const result = new Float32Array(newLength);
        let offsetResult = 0;
        let offsetBuffer = 0;

        while (offsetResult < result.length) {
            const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
            let accum = 0, count = 0;
            
            for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
                accum += buffer[i];
                count++;
            }
            
            result[offsetResult] = accum / count;
            offsetResult++;
            offsetBuffer = nextOffsetBuffer;
        }
        
        return result;
    }
}