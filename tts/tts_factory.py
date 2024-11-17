from tts.edge_tts import EdgeTTS

def get_tts(tts:str):
    if tts == "edge_tts":
        return EdgeTTS()
    return EdgeTTS()