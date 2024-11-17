from .Sambanova import SambaNova

base_url = "https://api.sambanova.ai/v1"
api_key = "b1463722-e182-437a-b294-8a4c867923fe"
LLAMA_405B = "Meta-Llama-3.1-405B-Instruct"


def get_llm(llm:str):
    if llm == "sambanova":
        return SambaNova("", base_url, api_key, LLAMA_405B, 0.01)
    return SambaNova("", base_url, api_key, LLAMA_405B, 0.01)