import request from '../utils/request';
import type { TranslationRequest, BatchTranslationRequest, Result, TranslationResponse, BatchTranslationResponse } from '../types/translation';

export function translateText(data: TranslationRequest) {
    return request.post<any, Result<TranslationResponse>>('/translation/text', data);
}

export function batchTranslate(data: BatchTranslationRequest) {
    return request.post<any, Result<BatchTranslationResponse>>('/translation/batch', data);
}

export function clearCache() {
    return request.post<any, Result<{cleared: boolean}>>('/translation/cache/clear');
}

export function getCacheStats() {
    return request.get<any, Result<any>>('/translation/cache/stats');
}
