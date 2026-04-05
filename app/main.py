from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.exceptions import AppException, app_exception_handler, validation_exception_handler, SupabaseNotInitializedException
from fastapi.exceptions import RequestValidationError
import httpx

# Setup logging
setup_logging(settings.log_level, settings.log_file)

# Create FastAPI application
app = FastAPI(
    title="BMS Cloud Platform API",
    description="户储 BMS 云平台核心业务中台 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


async def supabase_not_initialized_handler(request: Request, exc: SupabaseNotInitializedException):
    """Handle Supabase not initialized errors"""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": {
                "code": "DATABASE_UNAVAILABLE",
                "message": "Database service is currently unavailable",
                "details": {}
            }
        }
    )


app.add_exception_handler(SupabaseNotInitializedException, supabase_not_initialized_handler)

# Import and include API routers
from app.api.v1 import devices, alerts, thresholds, ota, commands, metrics

# Create global metrics collector
from app.services.batch_worker import MetricsCollector
metrics_collector = MetricsCollector()
metrics.set_metrics_collector(metrics_collector)

app.include_router(devices.router, prefix="/api/v1", tags=["devices"])
app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])
app.include_router(thresholds.router, prefix="/api/v1", tags=["thresholds"])
app.include_router(ota.router, prefix="/api/v1", tags=["ota"])
app.include_router(commands.router, prefix="/api/v1", tags=["commands"])
app.include_router(metrics.router)  # Metrics endpoints

# Import schedulers
from app.services.offline_detection import offline_detection_service
from app.services.ota_recovery import ota_recovery_service


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up BMS Cloud Platform API")
    logger.info(f"Supabase URL: {settings.supabase_url}")
    logger.info(f"EMQX Host: {settings.emqx_host}:{settings.emqx_port}")

    # Load active alerts into detector
    try:
        from app.services.alert_detector import alert_detector
        await alert_detector.load_active_alerts()
    except Exception as e:
        logger.error(f"Failed to load active alerts from database: {e}")
        logger.warning("Alert detector will start with empty state")

    # Start background schedulers
    offline_detection_service.start()
    ota_recovery_service.start()

    # Start MQTT subscription if enabled
    if getattr(settings, 'enable_mqtt_subscription', False):
        logger.info("Starting MQTT subscription service...")
        from app.services.mqtt_subscription_service import MqttSubscriptionService
        from app.services.batch_worker import BatchWorker
        import asyncio
        import httpx

        queue = asyncio.Queue(maxsize=10000)
        mqtt_service = MqttSubscriptionService(queue, metrics_collector, alert_detector)
        batch_worker = BatchWorker(queue, metrics_collector, alert_detector)
        http_client = httpx.AsyncClient(timeout=30.0)

        # Start background tasks
        asyncio.create_task(mqtt_service.run())
        asyncio.create_task(batch_worker.run(http_client))
        logger.info("MQTT subscription and batch worker started")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down BMS Cloud Platform API")
    # Stop background schedulers
    offline_detection_service.stop()
    ota_recovery_service.stop()
    # Stop MQTT subscription if enabled
    if getattr(settings, 'enable_mqtt_subscription', False):
        logger.info("Stopping MQTT subscription service...")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        reload=True
    )
