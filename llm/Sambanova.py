import os
import openai

from .abstract_llm import AbstractLLM

sentence_endings = {'.', '?', '!', '。', '？', '！'}

class SambaNova(AbstractLLM):

    def __init__(self, system: str, base_url: str, api_key:str, model:str, temperature: float):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.messages = []
        self.max_tokens = 4096
        if system and len(system) > 0:
            self.messages = [{"role":"system", "content": system}]
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    def chat(self, message:str):
        self.messages.append({"role": "user", "content": message})
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=0.1,
                stream=True,
            )

            # 先返回第一个句子，然后在一并返回剩下的句子，用于流式tts
            temp = ""
            response = ""
            first_chunk_returned = False
            for chunk in completion:
                temp += chunk.choices[0].delta.content or ""
                while any(p in temp for p in sentence_endings) and not first_chunk_returned:
                    sentence_end_index = min((temp.index(p) for p in sentence_endings if p in temp)) + 1
                    sentence = temp[:sentence_end_index]
                    first_chunk_returned = True
                    yield sentence
                    response += sentence
                    temp = temp[sentence_end_index:]
            if temp:
                yield temp
                response += temp

            # add message of this round
            self.messages.append({
                "role": "assistant",
                "content": response
            })

        except Exception as e:
            raise f"query sambanova failed, err is {e}"