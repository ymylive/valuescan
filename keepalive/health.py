"""
Health checking component for the Process Keepalive Service.

Responsible for checking service health via systemctl and journalctl.
"""

from typing import Tuple, Optional
from datetime import datetime, timezone
import subprocess
import logging
import re

from .config import ServiceConfig, ServiceState

logger = logging.getLogger(__name__)


class HealthChecker:
    """Checks service health status."""
    
    def __init__(self, command_timeout: int = 10):
        """
        Initialize the health checker.
        
        Args:
            command_timeout: Timeout for shell commands in seconds
        """
        self.command_timeout = command_timeout
    
    def check_service_active(self, service_name: str) -> bool:
        """
        Check if a service is in active state using systemctl.
        
        Args:
            service_name: The systemd service name
            
        Returns:
            True if service is active, False otherwise
            
        Requirements: 1.4, 2.1
        """
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=self.command_timeout
            )
            # systemctl is-active returns "active" if service is running
            status = result.stdout.strip().lower()
            is_active = status == "active"
            logger.debug(f"Service {service_name} status: {status}, is_active: {is_active}")
            return is_active
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout checking service {service_name} status")
            return False
        except Exception as e:
            logger.error(f"Error checking service {service_name} status: {e}")
            return False
    
    def get_last_log_time(self, service_name: str) -> Optional[datetime]:
        """
        Get the timestamp of the last log entry for a service using journalctl.
        
        Args:
            service_name: The systemd service name
            
        Returns:
            datetime of last log entry, or None if unavailable
            
        Requirements: 2.4
        """
        try:
            # Get the last log entry with ISO 8601 timestamp format
            result = subprocess.run(
                ["journalctl", "-u", service_name, "-n", "1", "--output=short-iso", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=self.command_timeout
            )
            
            if result.returncode != 0 or not result.stdout.strip():
                logger.debug(f"No journal logs found for {service_name}")
                return None
            
            # Parse the timestamp from journalctl output
            # Format: 2024-01-15T10:30:45+0800 hostname service[pid]: message
            # Or: 2024-01-15T10:30:45.123456+08:00 hostname service[pid]: message
            output = result.stdout.strip()
            return self._parse_journal_timestamp(output)
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout getting journal logs for {service_name}")
            return None
        except Exception as e:
            logger.error(f"Error getting journal logs for {service_name}: {e}")
            return None
    
    def _parse_journal_timestamp(self, log_line: str) -> Optional[datetime]:
        """
        Parse timestamp from a journalctl log line.
        
        Handles both timezone-aware and timezone-naive formats.
        
        Args:
            log_line: A single log line from journalctl
            
        Returns:
            Parsed datetime or None on failure
        """
        if not log_line:
            return None
        
        # Extract the timestamp part (first space-separated token)
        parts = log_line.split()
        if not parts:
            return None
        
        timestamp_str = parts[0]
        
        # Try various ISO 8601 formats
        formats = [
            # With timezone offset (e.g., 2024-01-15T10:30:45+0800)
            "%Y-%m-%dT%H:%M:%S%z",
            # With microseconds and timezone (e.g., 2024-01-15T10:30:45.123456+08:00)
            "%Y-%m-%dT%H:%M:%S.%f%z",
            # Without timezone (naive datetime)
            "%Y-%m-%dT%H:%M:%S",
            # With microseconds, no timezone
            "%Y-%m-%dT%H:%M:%S.%f",
        ]
        
        # Handle timezone offset format variations (e.g., +08:00 vs +0800)
        # Python's %z expects +HHMM or +HH:MM depending on version
        normalized_ts = timestamp_str
        # Try to normalize +HH:MM to +HHMM for older Python versions
        tz_match = re.search(r'([+-])(\d{2}):(\d{2})$', timestamp_str)
        if tz_match:
            normalized_ts = timestamp_str[:tz_match.start()] + tz_match.group(1) + tz_match.group(2) + tz_match.group(3)
        
        for fmt in formats:
            try:
                dt = datetime.strptime(normalized_ts, fmt)
                # If timezone-naive, assume local time and make it aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        
        # Also try the original timestamp string
        if normalized_ts != timestamp_str:
            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
        
        logger.warning(f"Could not parse timestamp: {timestamp_str}")
        return None
    
    def is_service_healthy(
        self, 
        config: ServiceConfig, 
        state: ServiceState,
        current_time: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        Determine if a service is healthy by combining status and log checks.
        
        Args:
            config: Service configuration
            state: Current service state
            current_time: Current time for testing (defaults to now)
            
        Returns:
            Tuple of (is_healthy, reason)
            
        Requirements: 2.1, 2.2, 2.3
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Check if service is disabled
        if not config.enabled:
            return True, "disabled"
        
        # Check systemctl active status (Requirement 2.1)
        is_active = self.check_service_active(config.name)
        if not is_active:
            logger.info(f"Service {config.name} is not active")
            return False, "inactive"
        
        # Skip no-log detection if threshold is null (Requirement 2.3)
        if config.no_log_threshold is None:
            return True, "active"
        
        # Check for stuck service via log activity (Requirement 2.2)
        last_log_time = self.get_last_log_time(config.name)
        if last_log_time is None:
            # No logs available, consider healthy if active
            logger.debug(f"No logs available for {config.name}, considering healthy")
            return True, "active"
        
        # Ensure both times are timezone-aware for comparison
        if last_log_time.tzinfo is None:
            last_log_time = last_log_time.replace(tzinfo=timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        
        # Calculate time since last log
        time_since_log = (current_time - last_log_time).total_seconds()
        
        if time_since_log > config.no_log_threshold:
            logger.info(
                f"Service {config.name} has no logs for {time_since_log:.0f}s "
                f"(threshold: {config.no_log_threshold}s)"
            )
            return False, "stuck"
        
        return True, "active"


def check_service_status_from_output(output: str) -> bool:
    """
    Check if a service is active based on systemctl output.
    
    This is a pure function for testing purposes.
    
    Args:
        output: The output from systemctl is-active command
        
    Returns:
        True if the output indicates active status, False otherwise
    """
    return output.strip().lower() == "active"


def is_service_stuck(
    last_log_time: Optional[datetime],
    current_time: datetime,
    no_log_threshold: Optional[int]
) -> bool:
    """
    Determine if a service is stuck based on log activity.
    
    This is a pure function for testing purposes.
    
    Args:
        last_log_time: Time of last log entry (None if no logs)
        current_time: Current time
        no_log_threshold: Threshold in seconds (None to disable check)
        
    Returns:
        True if service is considered stuck, False otherwise
    """
    # Skip check if threshold is None (Requirement 2.3)
    if no_log_threshold is None:
        return False
    
    # No logs available - not considered stuck
    if last_log_time is None:
        return False
    
    # Ensure both times are timezone-aware
    if last_log_time.tzinfo is None:
        last_log_time = last_log_time.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    
    time_since_log = (current_time - last_log_time).total_seconds()
    return time_since_log > no_log_threshold
