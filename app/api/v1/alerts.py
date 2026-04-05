from fastapi import APIRouter, Query, HTTPException, status, Body
from typing import Optional, List
from app.services.alert_service import alert_service
from app.core.exceptions import AlertNotFoundException
from app.schemas.alert import AlertListResponse, AlertStatsResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def get_alerts(
    device_id: Optional[str] = Query(None, description="设备 ID"),
    severity: Optional[int] = Query(None, description="告警级别"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    keyword: Optional[str] = Query(None, description="关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取告警列表"""
    result = await alert_service.get_alerts(
        device_id=device_id,
        severity=severity,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        page=page,
        page_size=page_size
    )
    return result


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    device_id: Optional[str] = Query(None, description="设备 ID"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期")
):
    """获取告警统计"""
    from loguru import logger
    logger.info("Calling alert_service.get_alert_stats()")
    result = await alert_service.get_alert_stats(
        device_id=device_id,
        start_date=start_date,
        end_date=end_date
    )
    logger.info(f"Stats result: total={result.get('total')}")
    return result


# Use close-multiple path to avoid conflict with /{alert_id}/close
@router.patch("/close-multiple")
async def bulk_close_alerts(
    alert_ids: List[int] = Body(..., description="告警 ID 列表"),
    device_id: Optional[str] = Body(None, description="设备 ID")
):
    """批量关闭告警"""
    result = await alert_service.bulk_close_alerts(alert_ids, device_id)
    return {"message": f"已关闭 {result['updated_count']} 条告警"}


@router.patch("/{alert_id}/close")
async def close_alert(alert_id: int):
    """关闭告警"""
    try:
        result = await alert_service.close_alert(alert_id)
        return {"message": "告警已关闭", "alert": result}
    except AlertNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message, "details": e.details}
        )
