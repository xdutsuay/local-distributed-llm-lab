"""
Base Tool Interface for LLM Lab

Defines the abstract base class that all tools must inherit from.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ToolInput(BaseModel):
    """Base schema for tool inputs with validation"""
    pass


class ToolOutput(BaseModel):
    """Base schema for tool outputs"""
    success: bool
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Tool(ABC):
    """
    Abstract base class for all tools in the system.
    
    Tools extend worker capabilities by providing specific functionality
    like web search, calculations, or browser automation.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this tool"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does"""
        pass
    
    @property
    def capabilities(self) -> List[str]:
        """List of capabilities this tool provides"""
        return [self.name]
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolOutput:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolOutput containing success status, result, and optional error
        """
        pass
    
    def validate_input(self, **kwargs) -> bool:
        """
        Validate input parameters before execution.
        Override for custom validation logic.
        """
        return True
    
    async def safe_execute(self, **kwargs) -> ToolOutput:
        """
        Execute with error handling wrapper.
        """
        try:
            if not self.validate_input(**kwargs):
                return ToolOutput(
                    success=False,
                    result=None,
                    error="Invalid input parameters"
                )
            
            return await self.execute(**kwargs)
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"{type(e).__name__}: {str(e)}"
            )
