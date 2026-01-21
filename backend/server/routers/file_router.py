from typing import Any
from fastapi import APIRouter
from src.schemas.result import Result
from src.service import file_service as FileService

router = APIRouter()
file_service = FileService.file_Service()

@router.post("/Upload", response_model=Result[Any], summary="上传文件")
def translate_text(files: List[UploadFile]):
    try:
        data = file_service.upload_file(files)
        return Result.success(data)
    except Exception as e:
        return Result.fail(500, f"上传文件失败: {str(e)}")

@router.post("/Delete_UnTranslated", response_model=Result[Any], summary="删除待翻译文件")
def delete_file(file_names: List[str]):
    try:
        data = file_service.delete_file_untranslated(file_names)
        return Result.success(data)
    except Exception as e:
        return Result.fail(500, f"删除文件失败: {str(e)}")

@router.post("/Delete_Translated", response_model=Result[Any], summary="删除已翻译文件")
def delete_file(file_names: List[str]):
    try:
        data = file_service.delete_file_translated(file_names)
        return Result.success(data)
    except Exception as e:
        return Result.fail(500, f"删除文件失败: {str(e)}")

# @router.post("/List_UnTranslated", response_model=Result[Any], summary="列出所有待翻译文件")
# def list_files():
#     try:
#         data = file_service.list_files()
#         return Result.success(data)
#     except Exception as e:
#         return Result.fail(500, f"列出文件失败: {str(e)}")

# @router.post("/List_Translated", response_model=Result[Any], summary="列出所有已翻译文件")
# def list_files():
#     try:
#         data = file_service.list_files()
#         return Result.success(data)
#     except Exception as e:
#         return Result.fail(500, f"列出文件失败: {str(e)}")