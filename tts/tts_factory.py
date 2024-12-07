from tts.edge_tts import EdgeTTS
from tts.vits_onnx_tts import VitsOnnx


def get_tts(tts:str):
    if tts == "edge_tts":
        return EdgeTTS()
    elif tts == "vits_onnx":
        return VitsOnnx()
    return EdgeTTS()