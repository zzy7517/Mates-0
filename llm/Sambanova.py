import os
import openai

from .abstract_llm import AbstractLLM

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

            response = ""
            for chunk in completion:
                response += chunk.choices[0].delta.content or ""
            self.messages.append({
                "role": "assistant",
                "content": response
            })
            return response
        except Exception as e:
            raise f"query sambanova failed, err is {e}"