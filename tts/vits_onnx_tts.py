# Copyright (c)  2023  Xiaomi Corporation

"""
This file demonstrates how to use sherpa-onnx Python API to generate audio
from text, i.e., text-to-speech.

streaming tts

You can find more models at
https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models

Please see
https://k2-fsa.github.io/sherpa/onnx/tts/index.html
for details.
"""

import logging
import os
import queue
import sys
import threading
import time

import numpy as np
import sherpa_onnx
import soundfile as sf
from sympy import false

try:
    import sounddevice as sd
except ImportError:
    print("Please install sounddevice first. You can use")
    print()
    print("  pip install sounddevice")
    print()
    print("to install it")
    sys.exit(-1)

base_dir = os.path.join(r"D:\python\Mates-0\sherpa-onnx-vits-zh-ll")

vits_model = os.path.join(base_dir, "model.onnx")
vits_lexicon = os.path.join(base_dir, "lexicon.txt")
vits_tokens = os.path.join(base_dir, "tokens.txt")
vits_dict_dir = os.path.join(base_dir, "dict")
vits_data_dir = "" #Path to the dict directory of espeak-ng. If it is specified,--vits-lexicon and --vits-tokens are ignored
phone_fst = os.path.join(base_dir, "phone.fst")
date_fst = os.path.join(base_dir, "date.fst")
number_fst = os.path.join(base_dir, "number.fst")
tts_rule_fsts = ",".join([phone_fst, date_fst, number_fst])
output_filename = "./test.wav"
sid = 2
provider = "cpu" # cpu, cuda, coreml
num_threads = 1
speed = 1.0
texta = "当夜幕降临，星光点点，伴随着微风拂面，我在静谧中感受着时光的流转，思念如涟漪荡漾，梦境如画卷展开，我与自然融为一体，沉静在这片宁静的美丽之中，感受着生命的奇迹与温柔。2024年5月11号，拨打110或者18920240511。123456块钱。"

class VitsOnnx:
    def __init__(self):
        self.buffer = queue.Queue() # buffer saves audio samples to be played
        self.started = False # started is set to True once generated_audio_callback is called.
        self.stopped = False # stopped is set to True once all the text has been processed
        self.event = threading.Event()
        self.first_message_time = None
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=vits_model,
                    lexicon=vits_lexicon,
                    data_dir=vits_data_dir,
                    dict_dir=vits_dict_dir,
                    tokens=vits_tokens,
                ),
                provider=provider,
                debug=false,
                num_threads=num_threads,
            ),
            rule_fsts=tts_rule_fsts,
            max_num_sentences=1,
        )
        if not tts_config.validate():
            raise ValueError("Please check your config")
        logging.info("Loading model ...")
        self.tts = sherpa_onnx.OfflineTts(tts_config)
        logging.info("Loading model done.")
        self.sample_rate = self.tts.sample_rate

    def generated_audio_callback(self,samples: np.ndarray, progress: float):
        """This function is called whenever max_num_sentences sentences
        have been processed.

        Note that it is passed to C++ and is invoked in C++.

        Args:
          samples:
            A 1-D np.float32 array containing audio samples
        """
        if self.first_message_time is None:
            self.first_message_time = time.time()
        self.buffer.put(samples)
        if self.started is False:
            logging.info("Start playing ...")
        self.started = True

        # 1 means to keep generating
        # 0 means to stop generating
        # if self.killed:
        # todo 打断
        #     return 0

        return 1


    # see https://python-sounddevice.readthedocs.io/en/0.4.6/api/streams.html#sounddevice.OutputStream
    def play_audio_callback(
        self, outdata: np.ndarray, frames: int, time, status: sd.CallbackFlags
    ):
        if self.started and self.buffer.empty() and self.stopped:
            self.event.set()

        # outdata is of shape (frames, num_channels)
        if self.buffer.empty():
            outdata.fill(0)
            return

        n = 0
        while n < frames and not self.buffer.empty():
            remaining = frames - n
            k = self.buffer.queue[0].shape[0]

            if remaining <= k:
                outdata[n:, 0] = self.buffer.queue[0][:remaining]
                self.buffer.queue[0] = self.buffer.queue[0][remaining:]
                n = frames
                if self.buffer.queue[0].shape[0] == 0:
                    self.buffer.get()

                break

            outdata[n : n + k, 0] = self.buffer.get()
            n += k

        if n < frames:
            outdata[n:, 0] = 0


    # Please see
    # https://python-sounddevice.readthedocs.io/en/0.4.6/usage.html#device-selection
    # for how to select a device
    def play_audio(self):
        # This if branch can be safely removed. It is here to show you how to
        # change the default output device in case you need that.
        devices = sd.query_devices()
        #print(devices)

        # sd.default.device[1] is the output device, if you want to
        # select a different device, say, 3, as the output device, please
        # use self.default.device[1] = 3
        default_output_device_idx = sd.default.device[1]
        print(
            f'Use default output device: {devices[default_output_device_idx]["name"]}'
        )

        with sd.OutputStream(
            channels=1,
            callback=self.play_audio_callback,
            dtype="float32",
            samplerate=self.sample_rate,
            blocksize=1024,
        ):
            self.event.wait()


    def speek(self, text):
        self.buffer = queue.Queue()
        self.started = False
        self.stopped = False
        self.first_message_time = None

        play_back_thread = threading.Thread(target=self.play_audio)
        play_back_thread.start()
        logging.info("Start generating ...")
        start_time = time.time()
        audio = self.tts.generate(
            text,
            sid=sid,
            speed=speed,
            callback=self.generated_audio_callback,
        )
        end_time = time.time()
        self.stopped = True
        if len(audio.samples) == 0:
            logging.error("Error in generating audios. Please read previous error messages.")
            play_back_thread.join()
            return

        elapsed_seconds = end_time - start_time
        audio_duration = len(audio.samples) / audio.sample_rate
        real_time_factor = elapsed_seconds / audio_duration

        sf.write(
            output_filename,
            audio.samples,
            samplerate=audio.sample_rate,
            subtype="PCM_16",
        )
        logging.info(f"The text is '{text}'")
        logging.info("Time in seconds to receive the first "f"message: {self.first_message_time-start_time:.3f}")
        #logging.info(f"Elapsed seconds: {elapsed_seconds:.3f}")
        #logging.info(f"Audio duration in seconds: {audio_duration:.3f}")
        logging.info(f"RTF: {elapsed_seconds:.3f}/{audio_duration:.3f} = {real_time_factor:.3f}")
        logging.info(f"***  Saved to {output_filename} ***")
        play_back_thread.join()