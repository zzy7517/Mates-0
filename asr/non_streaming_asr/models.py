from abc import abstractmethod, ABC
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
from enum import Enum

class AsrModelEnum(Enum):
    SenseVoice = 1
    Paraformer = 2


class ASRModel(ABC):
    @abstractmethod
    def transcribe(self, audio):
        pass

# asr model sensevoice
# https://www.modelscope.cn/models/iic/SenseVoiceSmall
class SenseVoice(ASRModel):
    def __init__(self, language):
        super().__init__()
        self.lan = language
        self.asr_model = pipeline(
            task=Tasks.auto_speech_recognition,
            model='iic/SenseVoiceSmall',
            model_revision="master",
            device="cuda:0",
        )

    def transcribe(self, audio):
        return self.asr_model(audio, language=self.lan)

# asr model paraformer
# https://www.modelscope.cn/models/iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch
class Paraformer(ASRModel):
    def __init__(self, language):
        super().__init__()
        self.lan = language
        self.asr_model = pipeline(
            task=Tasks.auto_speech_recognition,
            model="iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            #model_revision="master",
            device="cuda:0",
        )

    def transcribe(self, audio):
        return self.asr_model(audio, language=self.lan.strip())

def asr_model(model_type, language):
    models = {
        AsrModelEnum.SenseVoice: SenseVoice,
        AsrModelEnum.Paraformer: Paraformer,
    }

    if models.get(model_type):
        return models.get(model_type)(language)
    return SenseVoice(language)
