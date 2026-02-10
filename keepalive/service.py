"""
Main service class for the Process Keepalive Service.

Coordinates all components and runs the main monitoring loop.
"""

import signal
import time
import logging
import sys
from typing import Dict, List, Optional
from datetime import datetime

from .config import (
    ServiceConfig, ServiceState, GlobalConfig, TelegramConfig,
    KeepaliveConfig, load_config
)
from .health import HealthChecker
from .restarter import ServiceRestarter
from .alerter import Alerter

logger = logging.getLogger(__name__)


class KeepaliveService:
    """
    Main keepalive service coordinator.
    
    Coordinates health checking, restarting, and alerting for monitored services.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the keepalive service.
        
        Loads configuration from the specified path and initializes all components.
        
        Args:
            config_path: Path to the configuration file
            
        Requirements: 1.1, 1.2
        """
        self.config_path = config_path
        self.running = False
        self._shutdown_reason: Optional[str] = None
        
        # Load configuration (Requirement 1.1)
        self._load_configuration()
        
        # Initialize component instances
        self.health_checker = HealthChecker()
        self.restarter = ServiceRestarter()
        self.alerter = Alerter(telegram_config=self.telegram_config)
        
        # Initialize service states
        self.states: Dict[str, ServiceState] = {}
        for config in self.configs:
            self.states[config.name] = ServiceState()
        
        # Set up logging
        self._setup_logging()
        
        logger.info(f"KeepaliveService initialized with {len(self.configs)} services")
    
    def _load_configuration(self) -> None:
        """Load configuration from file."""
        keepalive_config = load_config(self.config_path)
        self.global_config: GlobalConfig = keepalive_config.global_config
        self.telegram_config: TelegramConfig = keepalive_config.telegram
        self.configs: List[ServiceConfig] = keepalive_config.services
    
    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        # Configure root logger if not already configured
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            # Set up console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            root_logger.setLevel(logging.INFO)
        
        # Try to add file handler if log_file is configured
        if self.global_config.log_file:
            try:
                file_handler = logging.FileHandler(
                    self.global_config.log_file,
                    encoding='utf-8'
                )
                file_handler.setLevel(logging.INFO)
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
                logger.info(f"Logging to file: {self.global_config.log_file}")
            except (IOError, PermissionError) as e:
                logger.warning(f"Could not open log file {self.global_config.log_file}: {e}")

    def _setup_signal_handlers(self) -> None:
        """
        Register signal handlers for graceful shutdown.
        
        Requirements: 6.3
        """
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        logger.debug("Signal handlers registered for SIGTERM and SIGINT")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        self._shutdown_reason = f"Received {signal_name}"
        logger.info(f"Received signal {signal_name}, initiating shutdown...")
        self.running = False
    
    def run(self) -> None:
        """
        Run the main monitoring loop.
        
        Iterates through configured services, performs health checks,
        and restarts unhealthy services as needed.
        
        Requirements: 1.3, 6.1
        """
        self._setup_signal_handlers()
        self.running = True
        
        logger.info("Starting keepalive service monitoring loop")
        
        while self.running:
            # Iterate through all configured services
            for config in self.configs:
                if not self.running:
                    break
                
                # Skip disabled services
                if not config.enabled:
                    logger.debug(f"Skipping disabled service: {config.name}")
                    continue
                
                try:
                    self.check_and_restart(config)
                except Exception as e:
                    # Handle per-service exceptions (Requirement 6.1)
                    logger.error(
                        f"Exception while checking service {config.name}: {e}",
                        exc_info=True
                    )
                    # Continue checking other services
                    continue
            
            if not self.running:
                break
            
            # Sleep for the global check interval (Requirement 1.3)
            # Use the minimum check_interval from all services, or global default
            sleep_interval = self._get_sleep_interval()
            logger.debug(f"Sleeping for {sleep_interval} seconds")
            
            # Sleep in small increments to allow quick shutdown response
            sleep_end = time.time() + sleep_interval
            while time.time() < sleep_end and self.running:
                time.sleep(min(1.0, sleep_end - time.time()))
        
        # Perform graceful shutdown
        self.shutdown()
    
    def _get_sleep_interval(self) -> int:
        """
        Get the sleep interval between check cycles.
        
        Returns the minimum check_interval from all enabled services,
        or the global default if no services are configured.
        
        Returns:
            Sleep interval in seconds
        """
        if not self.configs:
            return self.global_config.check_interval
        
        enabled_intervals = [
            config.check_interval 
            for config in self.configs 
            if config.enabled
        ]
        
        if not enabled_intervals:
            return self.global_config.check_interval
        
        return min(enabled_intervals)
    
    def check_and_restart(self, config: ServiceConfig) -> None:
        """
        Check a single service and restart if needed.
        
        Args:
            config: Service configuration to check
            
        Requirements: 1.3, 2.1, 3.1, 3.2, 4.1, 4.2, 6.1
        """
        state = self.states.get(config.name)
        if state is None:
            state = ServiceState()
            self.states[config.name] = state
        
        # Update last check time
        state.last_check = datetime.now()
        
        # Perform health check
        is_healthy, reason = self.health_checker.is_service_healthy(config, state)
        state.is_healthy = is_healthy
        
        if is_healthy:
            logger.debug(f"Service {config.name} is healthy: {reason}")
            return
        
        logger.warning(f"Service {config.name} is unhealthy: {reason}")
        
        # Check if we can restart (cooldown check)
        if not self.restarter.can_restart(config, state):
            logger.info(
                f"Service {config.name} is in cooldown period, skipping restart"
            )
            return
        
        # Attempt restart
        logger.info(f"Attempting to restart service {config.name}")
        success, error = self.restarter.restart_service(config.name, state)
        
        if success:
            # Send restart alert (Requirement 4.1)
            alert_msg = self.alerter.format_restart_alert(config, state, reason)
            self.alerter.send_alert(alert_msg)
        else:
            # Send error alert (Requirement 4.2)
            alert_msg = self.alerter.format_error_alert(config, error)
            self.alerter.send_alert(alert_msg)
    
    def shutdown(self) -> None:
        """
        Perform graceful shutdown.
        
        Logs the shutdown reason and performs cleanup.
        
        Requirements: 6.3
        """
        self.running = False
        
        if self._shutdown_reason:
            logger.info(f"Shutting down: {self._shutdown_reason}")
        else:
            logger.info("Shutting down keepalive service")
        
        # Log final statistics
        total_restarts = sum(state.restart_count for state in self.states.values())
        logger.info(f"Total restarts performed: {total_restarts}")
        
        for name, state in self.states.items():
            if state.restart_count > 0:
                logger.info(f"  {name}: {state.restart_count} restarts")
        
        logger.info("Keepalive service shutdown complete")
