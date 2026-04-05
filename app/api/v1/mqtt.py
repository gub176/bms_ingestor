from fastapi import APIRouter

router = APIRouter(prefix="/mqtt", tags=["mqtt"])

# MQTT webhook endpoints are now in the main commands router
# This router is kept for future MQTT-specific endpoints
