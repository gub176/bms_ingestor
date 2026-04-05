from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


# Custom exceptions
class AppException(Exception):
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}


class SupabaseNotInitializedException(AppException):
    def __init__(self, message: str = "Database connection not available"):
        super().__init__(
            code="DATABASE_UNAVAILABLE",
            message=message,
            details={}
        )


class DeviceNotFoundException(AppException):
    def __init__(self, device_id: str):
        super().__init__(
            code="DEVICE_NOT_FOUND",
            message="设备不存在或无权访问",
            details={"device_id": device_id}
        )


class DeviceOfflineException(AppException):
    def __init__(self, device_id: str):
        super().__init__(
            code="DEVICE_OFFLINE",
            message="设备离线，无法下发升级命令",
            details={"device_id": device_id}
        )


class AlertNotFoundException(AppException):
    def __init__(self, alert_id: str):
        super().__init__(
            code="ALERT_NOT_FOUND",
            message="告警不存在",
            details={"alert_id": alert_id}
        )


class OtaUpgradeNotFoundException(AppException):
    def __init__(self, upgrade_id: str):
        super().__init__(
            code="OTA_UPGRADE_NOT_FOUND",
            message="OTA 升级任务不存在",
            details={"upgrade_id": upgrade_id}
        )


class ThresholdNotFoundException(AppException):
    def __init__(self, device_id: str):
        super().__init__(
            code="THRESHOLD_NOT_FOUND",
            message="设备阈值配置不存在",
            details={"device_id": device_id}
        )


class CommandNotFoundException(AppException):
    def __init__(self, command_id: str):
        super().__init__(
            code="COMMAND_NOT_FOUND",
            message="命令不存在",
            details={"command_id": command_id}
        )


class DeviceAlreadyBoundException(AppException):
    def __init__(self, device_id: str):
        super().__init__(
            code="DEVICE_ALREADY_BOUND",
            message="设备已被绑定",
            details={"device_id": device_id}
        )


class InvalidTransitionException(AppException):
    def __init__(self, from_status: str, to_status: str):
        super().__init__(
            code="INVALID_TRANSITION",
            message=f"无效的 OTA 状态转换：{from_status} -> {to_status}",
            details={"from_status": from_status, "to_status": to_status}
        )


# Exception handlers
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "INVALID_PARAMS",
                "message": "请求参数验证失败",
                "details": exc.errors()
            }
        }
    )
