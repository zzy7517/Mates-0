import argparse
import asyncio
import logging
import traceback
import websockets
from asr.non_streaming_asr.asr_with_vad import ASR
from asr.non_streaming_asr.models import *
from llm.llm_factory import get_llm
from tts.tts_factory import get_tts

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s [File: %(filename)s, Line: %(lineno)d]'
)

def asr_call_back(message: str):
    for i, sentence in enumerate(LLM.chat(message)):
        TTS.send_speeking_task(sentence)

async def websocket_handler(websocket):
    try:
        async for message in websocket:
            logging.debug("[websocket_endpoint] websocket connected")
            ASR.process(message)
    except Exception as e:
        traceback.print_exc()
        logging.error(f"Unexpected error: {e}")
        await websocket.close()

async def main():
    async with websockets.serve(websocket_handler, "localhost", 27000):
        print("WebSocket server started on ws://localhost:27000")
        await asyncio.Future()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run the FastAPI app with a specified port.")
    parser.add_argument('--port', type=int, default=27000, help='Port number to run the FastAPI app on.')
    parser.add_argument('--language', type=str, default="zh", help='Language for the ASR model.')
    parser.add_argument('--asr', default=1, type=int, choices=[e.value for e in AsrModelEnum],
                        help='asr type to use')
    parser.add_argument('--llm', default="sambanova", help='Language model to use')
    parser.add_argument('--tts', default="vits_onnx", help='TTS model to use') # edge_tts
    args = parser.parse_args()
    LLM = get_llm(args.llm)
    TTS = get_tts(args.tts)
    ASR = ASR(asr_model(AsrModelEnum(args.asr), args.language), asr_call_back)
    asyncio.run(main())
    logging.info("server started")