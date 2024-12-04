import pyaudio
from pydub import AudioSegment

# ffmpeg is required, download it here https://www.gyan.dev/ffmpeg/builds/
# pyaudio non-streaming play api
def pyaudio_play_file(p, file_path):
    audio = AudioSegment.from_mp3(file_path)

    raw_data = audio.raw_data
    sample_width = audio.sample_width
    frame_rate = audio.frame_rate
    channels = audio.channels

    stream = p.open(format=p.get_format_from_width(sample_width),
                    channels=channels,
                    rate=frame_rate,
                    output=True)

    stream.write(raw_data)

    stream.stop_stream()
    stream.close()

    # p.terminate()