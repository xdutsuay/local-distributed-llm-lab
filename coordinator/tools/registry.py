"""
Tool Registry for LLM Lab

Manages available tools, routes tool calls, and tracks usage statistics.
"""
from typing import Dict, List, Optional, Any
from coordinator.tools.base import Tool, ToolOutput
from coordinator.tools.builtin_tools import BUILTIN_TOOLS


class ToolRegistry:
    """
    Central registry for all available tools in the system.
    """
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.usage_stats: Dict[str, int] = {}
        
        # Auto-register built-in tools
        for tool in BUILTIN_TOOLS:
            self.register(tool)
    
    def register(self, tool: Tool) -> None:
        """
        Register a new tool in the registry.
        
        Args:
            tool: Tool instance to register
        """
        if tool.name in self.tools:
            print(f"⚠️  Tool '{tool.name}' already registered, overwriting")
        
        self.tools[tool.name] = tool
        self.usage_stats[tool.name] = 0
        print(f"✓ Registered tool: {tool.name} - {tool.description}")
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """
        Retrieve a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, str]]:
        """
        List all available tools with their descriptions.
        
        Returns:
            List of tool metadata dicts
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "capabilities": tool.capabilities
            }
            for tool in self.tools.values()
        ]
    
    async def execute_tool(self, tool_name: str, **params) -> ToolOutput:
        """
        Execute a tool by name with given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            **params: Tool-specific parameters
            
        Returns:
            ToolOutput with result or error
        """
        tool = self.get_tool(tool_name)
        
        if not tool:
            return ToolOutput(
                success=False,
                result=None,
                error=f"Tool '{tool_name}' not found in registry"
            )
        
        # Track usage
        self.usage_stats[tool_name] += 1
        
        # Execute tool
        result = await tool.safe_execute(**params)
        
        return result
    
    def get_capabilities(self) -> List[str]:
        """
        Get all capabilities across all registered tools.
        
        Returns:
            List of capability strings
        """
        capabilities = []
        for tool in self.tools.values():
            capabilities.extend(tool.capabilities)
        return list(set(capabilities))
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get tool usage statistics.
        
        Returns:
            Dict with usage counts and tool info
        """
        return {
            "total_tools": len(self.tools),
            "total_executions": sum(self.usage_stats.values()),
            "usage_by_tool": self.usage_stats.copy(),
            "available_tools": [tool.name for tool in self.tools.values()]
        }
    
    def find_tools_by_capability(self, capability: str) -> List[Tool]:
        """
        Find tools that provide a specific capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of matching tools
        """
        return [
            tool for tool in self.tools.values()
            if capability in tool.capabilities
        ]


# Global tool registry instance
_global_registry = None

def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance (singleton)"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
