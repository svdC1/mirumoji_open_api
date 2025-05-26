# main.py
import logging
import re
import time
from fastapi import (APIRouter,
                     Query,
                     HTTPException)
from fastapi.responses import StreamingResponse
from processing.Processor import Processor
from models.ChatRequest import ChatRequest
from models.BreakdownRequest import BreakdownRequest
from models.BreakdownResponse import BreakdownResponse
from models.CustomBreakdownRequest import CustomBreakdownRequest
from utils.stream_utils import sse_gen

logger = logging.getLogger(__name__)

processor = Processor()
breakdown_service = processor.sentence_breakdown_service

gpt_router = APIRouter(prefix='/gpt')


@gpt_router.post("/breakdown", response_model=BreakdownResponse)
async def breakdown(req: BreakdownRequest):
    """
    Returns:
      - tokens: list of {surface, lemma, reading, pos, meaning, jlpt}
      - focus: the focus word (or None)
      - gpt_explanation: Cure Dolly–style breakdown text
    """
    try:
        m = f"Breakdown Request: sentence={req.sentence!r} focus={req.focus!r}"
        logger.info(m)
        t0 = time.perf_counter()
        result = breakdown_service.explain(req.sentence,
                                           req.focus)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(f"Request Time: {elapsed:.1f} ms")
        return result
    except Exception as e:
        logger.warning("Breakdown Failed: %s", e)
        # Strip fullwidth parentheses and retry
        cleaned = re.sub(r"[（）]",
                         "",
                         req.sentence)
        logger.info("Retrying with clean sentence: %r", cleaned)
        try:
            t0 = time.perf_counter()
            result = breakdown_service.explain(cleaned,
                                               req.focus)
            elapsed = (time.perf_counter() - t0) * 1000
            logger.info(f"Request Time: {elapsed:.1f} ms")
            # preserve the original in the response
            result_dict = result if isinstance(result,
                                               dict) else result.model_dump()
            result_dict["sentence"] = req.sentence
            return result_dict
        except Exception as e2:
            logger.exception("Retry failed")
            raise HTTPException(status_code=500, detail=str(e2))


@gpt_router.post("/custom_breakdown", response_model=BreakdownResponse)
async def custom_breakdown(req: CustomBreakdownRequest):
    """
    Returns:
      - tokens: list of {surface, lemma, reading, pos, meaning, jlpt}
      - focus: the focus word (or None)
      - gpt_explanation: Cure Dolly–style breakdown text
    """
    try:
        m = f"Breakdown Request: sentence={req.sentence!r} focus={req.focus!r}"
        logger.info(m)
        t0 = time.perf_counter()
        result = breakdown_service.explain_custom(req.sentence,
                                                  req.sysMsg,
                                                  req.prompt,
                                                  req.focus)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(f"Request Time: {elapsed:.1f} ms")
        return result
    except Exception as e:
        logger.warning("Breakdown Failed: %s", e)
        # Strip fullwidth parentheses and retry
        cleaned = re.sub(r"[（）]",
                         "",
                         req.sentence)
        logger.info("Retrying with clean sentence: %r", cleaned)
        try:
            t0 = time.perf_counter()
            result = breakdown_service.explain_custom(cleaned,
                                                      req.sysMsg,
                                                      req.prompt,
                                                      req.focus)
            elapsed = (time.perf_counter() - t0) * 1000
            logger.info(f"Request Time: {elapsed:.1f} ms")
            # preserve the original in the response
            result_dict = result if isinstance(result,
                                               dict) else result.model_dump()
            result_dict["sentence"] = req.sentence
            return result_dict
        except Exception as e2:
            logger.exception("Retry failed")
            raise HTTPException(status_code=500, detail=str(e2))


# ───────────────────────────────────────────────────────────
# 2) Full-sentence explanation (no focus word)
# ───────────────────────────────────────────────────────────
@gpt_router.get(
    "/explain",
    summary="Cure Dolly–style full sentence explanation",
)
async def explain_sentence(
    sentence: str = Query(..., description="Japanese sentence to explain"
                          )):
    """
    This endpoint returns only the GPT explanation, letting the model
    handle clause splitting and full structural breakdown.
    """
    try:
        txt = breakdown_service.gpt_explainer.explain_sentence(sentence)
        return {"sentence": sentence, "explanation": txt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@gpt_router.post("/stream")
async def chat_stream(req: ChatRequest):
    try:
        return StreamingResponse(sse_gen(req.model,
                                         req.system_message,
                                         req.prompt),
                                 media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(400, str(e))
