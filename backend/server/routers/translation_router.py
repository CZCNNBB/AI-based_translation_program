from typing import Any
from fastapi import APIRouter
from src.schemas.translation_schemas import TranslationRequest, BatchTranslationRequest
from src.schemas.result import Result
from src.service import translation_service as TranslationService

router = APIRouter()
translation_service = TranslationService.translation_Service()


@router.post("/text", response_model=Result[Any], summary="单文本翻译")
def translate_text(request: TranslationRequest):
    try:
        data = translation_service.translate_text(
            text=request.text,
            target_lang=request.target_lang,
            domain=request.domain,
            glossary=request.glossary,
            summary=request.summary,
        )
        return Result.success(data)
    except Exception as e:
        return Result.fail(500, f"翻译失败: {str(e)}")


@router.post("/batch", response_model=Result[Any], summary="批量翻译")
def batch_translate(request: BatchTranslationRequest):
    try:
        data = translation_service.batch_translate(
            input_dir=request.input_dir,
            output_dir=request.output_dir,
            target_lang=request.target_lang,
            domain=request.domain,
            glossary=request.glossary,
            summary=request.summary,
            file_pattern=request.file_pattern,
            delete_after=request.delete_after,
            batch_config=request.batch_config,
        )
        return Result.success(data)
    except Exception as e:
        return Result.fail(500, f"批量翻译失败: {str(e)}")


@router.post("/cache/clear", response_model=Result[Any], summary="清理语言检测缓存")
def clear_cache():
    try:
        cleared = translation_service.clear_cache()
        return Result.success({"cleared": cleared})
    except Exception as e:
        return Result.fail(500, f"清理缓存失败: {str(e)}")


@router.get("/cache/stats", response_model=Result[Any], summary="语言检测缓存统计")
def cache_stats():
    try:
        data = translation_service.cache_stats()
        return Result.success(data)
    except Exception as e:
        return Result.fail(500, f"获取缓存统计失败: {str(e)}")


