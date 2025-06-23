"""Base agent class for the multi-agent document translation system."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class AgentMessage(BaseModel):
    """Message structure for agent communication."""
    
    agent_id: str
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None


class AgentResult(BaseModel):
    """Result structure for agent operations."""
    
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None


class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.config = config
        self.logger = self._setup_logger()
        self.is_running = False
        self.message_queue = asyncio.Queue()
        
    def _setup_logger(self) -> logging.Logger:
        """Set up logger for the agent."""
        logger = logging.getLogger(f"agent.{self.agent_id}")
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        logs_dir = Path(self.config.get("logs_dir", "logs"))
        logs_dir.mkdir(exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(logs_dir / f"{self.agent_id}.log")
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    async def start(self):
        """Start the agent."""
        self.logger.info(f"Starting agent {self.agent_id}")
        self.is_running = True
        await self._initialize()
    
    async def stop(self):
        """Stop the agent."""
        self.logger.info(f"Stopping agent {self.agent_id}")
        self.is_running = False
        await self._cleanup()
    
    async def send_message(self, target_agent: str, message_type: str, content: Dict[str, Any], correlation_id: Optional[str] = None):
        """Send a message to another agent."""
        message = AgentMessage(
            agent_id=self.agent_id,
            message_type=message_type,
            content=content,
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )
        
        self.logger.info(f"Sending message to {target_agent}: {message_type}")
        # In a real implementation, this would use the A2A protocol
        # For now, we'll use a simple message passing mechanism
        
    async def receive_message(self) -> Optional[AgentMessage]:
        """Receive a message from the queue."""
        try:
            message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
            self.logger.info(f"Received message: {message.message_type} from {message.agent_id}")
            return message
        except asyncio.TimeoutError:
            return None
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process input data and return result."""
        pass
    
    @abstractmethod
    async def _initialize(self):
        """Initialize agent-specific resources."""
        pass
    
    @abstractmethod
    async def _cleanup(self):
        """Clean up agent-specific resources."""
        pass
    
    def _create_temp_dir(self) -> Path:
        """Create a temporary directory for this agent."""
        temp_dir = Path(self.config.get("temp_dir", "temp")) / self.agent_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
    
    def _validate_input(self, input_data: Dict[str, Any], required_fields: list) -> bool:
        """Validate input data contains required fields."""
        for field in required_fields:
            if field not in input_data:
                self.logger.error(f"Missing required field: {field}")
                return False
        return True

