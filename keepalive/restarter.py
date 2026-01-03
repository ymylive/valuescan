"""
Service restart component for the Process Keepalive Service.

Responsible for executing service restarts with cooldown enforcement.
"""

from typing import Tuple
from datetime import datetime
import subprocess
import logging

from .config import ServiceConfig, ServiceState

logger = logging.getLogger(__name__)


class ServiceRestarter:
    """Handles service restart operations."""
    
    def __init__(self, command_timeout: int = 30):
        """
        Initialize the service restarter.
        
        Args:
            command_timeout: Timeout for restart commands in seconds
        """
        self.command_timeout = command_timeout
    
    def can_restart(self, config: ServiceConfig, state: ServiceState) -> bool:
        """
        Check if a service can be restarted (cooldown check).
        
        Per Requirement 3.2: WHILE a Monitored_Service was restarted within its 
        Restart_Cooldown period THEN the Process_Keepalive_Service SHALL skip 
        the restart attempt.
        
        Args:
            config: Service configuration
            state: Current service state
            
        Returns:
            True if restart is allowed, False if in cooldown
        """
        # If never restarted before, allow restart
        if state.last_restart is None:
            return True
        
        # Calculate time since last restart
        now = datetime.now()
        time_since_restart = (now - state.last_restart).total_seconds()
        
        # Allow restart only if cooldown period has passed
        return time_since_restart >= config.restart_cooldown
    
    def restart_service(self, service_name: str, state: ServiceState) -> Tuple[bool, str]:
        """
        Execute a service restart using systemctl.
        
        Per Requirement 3.1: WHEN a Monitored_Service is marked unhealthy THEN 
        the Process_Keepalive_Service SHALL attempt to restart the Monitored_Service 
        using systemctl restart.
        
        Per Requirement 3.3: WHEN a restart is successful THEN the 
        Process_Keepalive_Service SHALL increment the restart counter.
        
        Per Requirement 3.4: WHEN a restart fails THEN the Process_Keepalive_Service 
        SHALL log the error message and continue monitoring.
        
        Args:
            service_name: The systemd service name
            state: Service state to update on success
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            result = subprocess.run(
                ["systemctl", "restart", service_name],
                capture_output=True,
                text=True,
                timeout=self.command_timeout
            )
            
            if result.returncode == 0:
                # Update state on success (Requirement 3.3)
                state.restart_count += 1
                state.last_restart = datetime.now()
                logger.info(f"Successfully restarted service '{service_name}', restart count: {state.restart_count}")
                return True, ""
            else:
                error_msg = result.stderr.strip() or f"systemctl returned code {result.returncode}"
                logger.error(f"Failed to restart service '{service_name}': {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            error_msg = f"Restart command timed out after {self.command_timeout} seconds"
            logger.error(f"Failed to restart service '{service_name}': {error_msg}")
            return False, error_msg
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to restart service '{service_name}': {error_msg}")
            return False, error_msg
