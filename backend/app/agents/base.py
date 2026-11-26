"""
Base Agent Abstract Interface
=============================
Defines the common lifecycle, logging, and execution contracts for all agents.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("neurolearn.agents")


class BaseAgent(ABC):
    """
    Abstract base agent ensuring unified lifecycle, execution interface,
    and structured error handling across all learning elements.
    """

    def __init__(self, name: str, element_role: str) -> None:
        self.name = name
        self.element_role = element_role
        self.logger = logging.getLogger(f"neurolearn.agents.{name}")

    @abstractmethod
    def run(self, context: Any, **kwargs) -> Any:
        """
        Executes the agent's core decision logic on the given context.
        Must be implemented by subclasses.
        """
        pass

    def log_execution(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Structured logging helper."""
        self.logger.info(
            "Agent [%s | %s] performed '%s'. Details: %s",
            self.name,
            self.element_role,
            action,
            details or {},
        )
