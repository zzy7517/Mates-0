import asyncio
import logging
import os

import playsound

import edge_tts

class EdgeTTS:
    def speek(self, text):
        try:
            # zh-CN-YunxiNeural
            # zh-CN-YunjianNeural
            # zh-CN-YunyangNeural
            communicate = edge_tts.Communicate(
                text=text,
                voice="zh-CN-XiaoxiaoNeural",
                rate="+35%"  # rate='+/-25%'
            )

            full_path = os.path.join("temp.mp3")
            full_path = r"{}".format(full_path)
            asyncio.run(communicate.save(full_path))

            if os.path.exists(full_path):
                logging.info("start speak")
                playsound.playsound(full_path)
                os.remove(full_path)

        except Exception as e:
            print(f"An unexpected error occurred, error: {e}")