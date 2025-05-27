# modal_runner.py
from typing import Dict
import modal
import logging
from processing.whisper_wrapper import FWhisperWrapper
from processing.audio_processing import AudioTools
from pathlib import Path
from dotenv import load_dotenv
import tempfile

load_dotenv()
logger = logging.getLogger(__name__)


docker_fp = Path("./modal_function/Dockerfile")
image = modal.Image.from_dockerfile(path=docker_fp,
                                    context_dir=docker_fp.parents[1])

stub = modal.Stub('mirumoji-open-source', image=image)


def _materialise(blob: bytes, suffix=".wav") -> Path:
    fp = Path(tempfile.mkstemp(suffix=suffix)[1])
    fp.write_bytes(blob)
    return fp


@stub.function(
    gpu="A10G",
    timeout=600,
)
def transcribe_to_srt(audio: bytes,
                      suffix: str,
                      OPENAI_API_KEY: str,
                      whisper_kwargs: Dict = {}
                      ) -> str:

    logging.basicConfig(level=logging.INFO,
                        style="{",
                        format="{levelname}-{name}-{message}"
                        )

    fp = _materialise(audio,
                      suffix)

    wrapper = FWhisperWrapper()
    srt_text = wrapper.transcribe_to_srt(
        audio_path=str(fp),
        output_path=fp.with_suffix(".srt"),
        string_result=True,
        transcribe_kwargs=whisper_kwargs,
        gpt_model_kwargs={"ApiKey": OPENAI_API_KEY}
    )
    return srt_text


@stub.function(gpu="A10G", timeout=600)
def transcribe_to_string(audio: bytes,
                         suffix: str,
                         clean_audio: bool = False,
                         whisper_kwargs: Dict = {}) -> str:

    logging.basicConfig(level=logging.INFO,
                        style="{",
                        format="{levelname}-{name}-{message}"
                        )

    fp = _materialise(audio,
                      suffix)
    # optional cleaning / re-encoding
    tools = AudioTools(".")
    if clean_audio:
        cleaned = fp.with_name(f"{fp.stem}-cleaned.wav")
        tools.filter_audio(str(fp), output_wav=str(cleaned))
        fp = cleaned

    wrapper = FWhisperWrapper()
    return wrapper.transcribe_to_str(str(fp), **whisper_kwargs)


@stub.function(gpu="A10G", timeout=600)
def video_to_mp4(video: bytes,
                 suffix: str,
                 use_nvenc: bool = True,
                 return_bytes: bool = False):
    """
    If `return_bytes` is True **and** the result is <100 MB we stream it back.
    Otherwise we drop it into a shared `modal.Volume` and send the path back.
    """
    logging.basicConfig(level=logging.INFO,
                        style="{",
                        format="{levelname}-{name}-{message}"
                        )

    in_fp = _materialise(video,
                         suffix)
    out_fp = in_fp.with_suffix(".mp4")

    tools = AudioTools(".")
    tools.to_mp4(str(in_fp),
                 output_path=str(out_fp),
                 use_nvenc=use_nvenc)

    if return_bytes and out_fp.stat().st_size < 100 * 1024 ** 2:
        return out_fp.read_bytes()

    # ---------- large file branch ----------
    vol = modal.Volume.persisted("mirumoji-results")
    dst = f"/{out_fp.name}"
    vol.add_local_file(dst, str(out_fp))
    return {"volume_path": dst}
