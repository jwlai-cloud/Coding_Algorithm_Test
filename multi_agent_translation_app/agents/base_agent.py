"""Base agent class for the Multi-Agent Document Translation App."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class AgentMessage:
    """Message structure for agent communication."""
    sender: str
    receiver: str
    message_type: str
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None
    timestamp: Optional[float] = None


@dataclass
class AgentResult:
    """Result structure for agent operations."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseAgent(ABC):
    """Base class for all agents in the translation system."""
    
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.status = AgentStatus.IDLE
        self.message_queue = asyncio.Queue()
        self.logger = logger.bind(agent=self.name)
        
    async def start(self):
        """Start the agent."""
        self.logger.info(f"Starting agent {self.name}")
        self.status = AgentStatus.RUNNING
        
    async def stop(self):
        """Stop the agent."""
        self.logger.info(f"Stopping agent {self.name}")
        self.status = AgentStatus.IDLE
        
    async def send_message(self, receiver: str, message_type: str, payload: Dict[str, Any], correlation_id: Optional[str] = None):
        """Send a message to another agent."""
        message = AgentMessage(
            sender=self.agent_id,
            receiver=receiver,
            message_type=message_type,
            payload=payload,
            correlation_id=correlation_id,
            timestamp=asyncio.get_event_loop().time()
        )
        self.logger.debug(f"Sending message to {receiver}: {message_type}")
        # In a real implementation, this would use the ADK's A2A protocol
        # For now, we'll simulate message passing
        return message
        
    async def receive_message(self) -> AgentMessage:
        """Receive a message from the queue."""
        return await self.message_queue.get()
        
    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=settings.RETRY_DELAY, min=1, max=10)
    )
    async def execute_with_retry(self, operation, *args, **kwargs):
        """Execute an operation with retry logic."""
        try:
            self.status = AgentStatus.RUNNING
            result = await operation(*args, **kwargs)
            self.status = AgentStatus.COMPLETED
            return result
        except Exception as e:
            self.status = AgentStatus.RETRYING
            self.logger.warning(f"Operation failed, retrying: {str(e)}")
            raise
            
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process input data and return result."""
        pass
        
    @abstractmethod
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data."""
        pass
        
    def get_status(self) -> AgentStatus:
        """Get current agent status."""
        return self.status

