from abc import ABC, abstractmethod

class AbstractLLM(ABC):
    @abstractmethod
    def chat(self, message:str):
        pass

