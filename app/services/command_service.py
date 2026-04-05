from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from app.db.supabase import supabase
from app.core.exceptions import CommandNotFoundException


class CommandService:
    """Remote command service"""

    async def create_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new remote command"""
        command_data = {
            "device_id": device_id,
            "command": command,
            "params": params or {},
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("remote_adjust") \
            .insert(command_data) \
            .execute()

        logger.info(f"Remote command created for device {device_id}: {command}")
        return result.data[0] if result.data else command_data

    async def get_command_by_id(self, command_id: str) -> Dict[str, Any]:
        """Get command by ID"""
        result = supabase.table("remote_adjust") \
            .select("*") \
            .eq("id", command_id) \
            .execute()

        if not result.data:
            raise CommandNotFoundException(command_id)

        return result.data[0]

    async def update_command_status(
        self,
        command_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update command execution status"""
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }

        if result:
            update_data["result"] = result
        if error_message:
            update_data["error_message"] = error_message
        if status in ["success", "failed"]:
            update_data["completed_at"] = datetime.utcnow().isoformat()

        result = supabase.table("remote_adjust") \
            .update(update_data) \
            .eq("id", command_id) \
            .execute()

        logger.info(f"Command {command_id} status updated: {status}")
        return result.data[0] if result.data else update_data

    async def get_commands(
        self,
        device_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Get command list with pagination"""
        query = supabase.table("remote_adjust").select("*", count="exact")

        if device_id:
            query = query.eq("device_id", device_id)
        if status:
            query = query.eq("status", status)

        result = query.execute()
        commands = result.data if hasattr(result, 'data') else []
        total = result.count if hasattr(result, 'count') else len(commands)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_commands = commands[start_idx:end_idx]

        return {
            "commands": paginated_commands,
            "total": total,
            "page": page,
            "page_size": page_size
        }


command_service = CommandService()
