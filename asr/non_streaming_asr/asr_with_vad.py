import logging
import time

import numpy as np
import re
import torch
from silero_vad import VADIterator
from pydantic import BaseModel


logger = logging.getLogger(__name__)

chunk_size_ms = 200 # Chunk size in milliseconds
sample_rate = 16000 # Sample rate in Hz
bit_depth = 16 # bit depth
channels = 1 # Number of audio channels
min_silence_duration_ms = 1500 # Minimum silence duration in milliseconds
threshold = 0.5 # Threshold for silence detection
speech_pad_ms = 100 # Final speech chunks are padded by speech_pad_ms each side

class ASR:
    def __init__(self, asr_pipeline, transcription_callback):
        self.vad_model, self.utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=True
        )
        self.vad_iterator = VADIterator(
            self.vad_model,
            sampling_rate=sample_rate,
            min_silence_duration_ms=min_silence_duration_ms,
            threshold=threshold,
            speech_pad_ms=speech_pad_ms
        )
        self.vad_iterator.reset_states()
        self.asr_pipeline = asr_pipeline
        self.chunk_size = 512  # silero vad 需要chunk_size 512
        self.audio_buffer = np.array([])
        self.audio_vad = np.array([])
        self.speech_timestamps = []
        self.last_end = 0
        self.offset = 0
        self.transcription_callback = transcription_callback

    class TranscriptionResponse(BaseModel):
        code: int
        msg: str
        data: str
        time_cost: float

    def format_str(self, text):
        return re.sub(r'<[^>]*>', '', text)

    def process_audio(self, audio):
        logging.debug(f"[process_vad_audio] process audio(length: {len(audio)})")
        return self.asr_pipeline.transcribe(audio)

    # get audio chunk form audio buffer
    def process_audio_chunk(self):
        chunk = self.audio_buffer[:self.chunk_size]
        self.audio_buffer = self.audio_buffer[self.chunk_size:]
        return chunk

    # add audio chunk to vad buffer and check
    def process_vad(self, chunk):
        self.audio_vad = np.append(self.audio_vad, chunk)
        speech_dict = self.vad_iterator(chunk, return_seconds=True)
        if speech_dict:
            self.speech_timestamps.append(speech_dict)
        if speech_dict and 'start' in speech_dict:
            if speech_dict['start'] > 0:
                self.last_end = speech_dict['start']

    # get meaningful audio segment from vad buffer
    def handle_speech_segment(self):
        start_sample = int(self.last_end * sample_rate) - int(self.offset * sample_rate)
        end_sample = int(self.speech_timestamps[-1]['end'] * sample_rate) - int(self.offset * sample_rate)
        audio_segment = self.audio_vad[start_sample:end_sample]
        self.audio_vad = self.audio_vad[end_sample:]
        self.last_end = self.speech_timestamps[-1]['end']
        self.offset = self.last_end
        self.speech_timestamps = []
        return audio_segment

    def cleanup(self):
        self.audio_buffer = np.array([])
        self.audio_vad = np.array([])
        self.vad_iterator.reset_states()
        logger.info("Cleaned up resources after WebSocket disconnect")

    def process(self, data):
        logging.debug(f"received {len(data)} bytes")
        self.audio_buffer = np.append(self.audio_buffer,
                                      np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0)

        while len(self.audio_buffer) >= self.chunk_size:
            chunk = self.process_audio_chunk()
            self.process_vad(chunk)
            if self.speech_timestamps and 'end' in self.speech_timestamps[-1] and (
                    self.speech_timestamps[-1]['end'] - self.last_end) > 0.5:
                audio_segment = self.handle_speech_segment()
                start_time = time.time()
                result = self.process_audio(audio_segment)
                logging.info(f"[process_vad_audio] {result}")

                if result is not None and len(result) > 0:
                    response = self.TranscriptionResponse(
                        code=0,
                        msg="success",
                        data=self.format_str(result[0]['text']),
                        time_cost=time.time() - start_time
                    )
                    logging.info(f"asr result {self.format_str(result[0]['text'])}, time cost {time.time()-start_time}")
                    self.transcription_callback(self.format_str(result[0]['text']))
                    # await websocket.send(json.dumps(response.dict()))