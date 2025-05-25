from typing import Optional, Union, Dict
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import logging
from processing.text_processing import SentenceBreakdownService
from processing.audio_processing import AudioTools
from processing.whisper_wrapper import FWhisperWrapper
from dotenv import load_dotenv


class Processor:
    """
    Wrapper for 'processing' module utilities.
    """
    def __init__(
        self,
        save_path: Union[str, Path, None] = None,
        use_modal: bool = False,
        gpt_version: str = "gpt-4.1-mini",
        dotenv_path: Union[str, Path, None] = None,
        whisper_kwargs: Dict = {},
        OPENAI_API_KEY: Optional[str] = None,
        MODAL_TOKEN_ID: Optional[str] = None,
        MODAL_TOKEN_SECRET: Optional[str] = None
    ) -> None:

        """
        Initalize instance with API Keys or collect from
        environment variables
        """
        self.logger = logging.getLogger(__class__.__name__)
        # Configure Save Path
        if not save_path:
            self.save_path = TemporaryDirectory(ignore_cleanup_errors=True)
        else:
            self.save_path = Path(save_path).resolve()
            if not self.save_path.is_dir():
                raise FileNotFoundError(f"Dir: '{save_path}' does not exist")
        # Configure API Keys
        load_dotenv(dotenv_path=dotenv_path)
        if use_modal:
            expected_keys = ["OPENAI_API_KEY",
                             "MODAL_TOKEN_ID",
                             "MODAL_TOKEN_SECRET"]
        else:
            self.logger.info("Not using Modal")
            expected_keys = ["OPENAI_API_KEY"]
        self.use_modal = use_modal
        API_KEYS = {k: v for k, v in os.environ.items() if k in expected_keys}
        self.logger.info(f"Retrieved {','.join(API_KEYS.keys())} from ENV")
        missing_keys = [k for k in expected_keys if k not in API_KEYS.keys()]
        self.logger.info(f"{','.join(missing_keys)} not found in ENV")
        if missing_keys:
            for mk in missing_keys:
                if mk == expected_keys[0]:
                    if not OPENAI_API_KEY:
                        raise ValueError("Could not find OPENAI_API_KEY")
                    API_KEYS[expected_keys[0]] = OPENAI_API_KEY
                elif mk == expected_keys[1]:
                    if not MODAL_TOKEN_ID:
                        raise ValueError("Could not find MODAL_TOKEN_ID")
                    API_KEYS[expected_keys[1]] = MODAL_TOKEN_ID
                elif mk == expected_keys[2]:
                    if not MODAL_TOKEN_SECRET:
                        raise ValueError("Could not find MODAL_TOKEN_SECRET")
                    API_KEYS[expected_keys[2]] = MODAL_TOKEN_SECRET
        self.API_KEYS = API_KEYS
        # Initializing Instances
        gpt_kwargs = {"from_dotenv": False,
                      "ApiKey": self.API_KEYS[expected_keys[0]]}
        self.sentence_breakdown_service = SentenceBreakdownService(gpt_version,
                                                                   gpt_kwargs)
        if not save_path:
            self.audio_tools = AudioTools(self.save_path.name)
        else:
            self.audio_tools = AudioTools(self.save_path)
        self.fwhisper = FWhisperWrapper(**whisper_kwargs)
        self.logger.info("Processor Initialized")

    def __del__(self):
        if isinstance(self.save_path, TemporaryDirectory):
            self.save_path.cleanup()
