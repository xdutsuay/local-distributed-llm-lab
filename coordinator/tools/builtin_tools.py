"""
Built-in Tools for LLM Lab

Provides example tool implementations:
- CalculatorTool: Basic arithmetic operations
- WebSearchTool: Web search simulation
- TextProcessorTool: String manipulation
"""
import math
import re
from typing import Dict, Any
from coordinator.tools.base import Tool, ToolOutput


class CalculatorTool(Tool):
    """Evaluate mathematical expressions safely"""
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "Evaluates mathematical expressions. Supports +, -, *, /, **, sqrt, sin, cos, log"
    
    async def execute(self, expression: str, **kwargs) -> ToolOutput:
        """
        Evaluate a mathematical expression.
        
        Args:
            expression: Mathematical expression to evaluate (e.g., "2 + 2", "sqrt(16)")
        """
        try:
            # Sanitize input - only allow safe math operations
            allowed_names = {
                'sqrt': math.sqrt,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'log': math.log,
                'log10': math.log10,
                'pi': math.pi,
                'e': math.e
            }
            
            # Remove any potentially dangerous characters
            if any(char in expression for char in ['__', 'import', 'eval', 'exec']):
                raise ValueError("Invalid expression - contains forbidden operations")
            
            # Evaluate safely
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={"expression": expression}
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"Calculation error: {str(e)}"
            )


class WebSearchTool(Tool):
    """Simulate web search (mock implementation)"""
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "Searches the web for information (mock implementation)"
    
    async def execute(self, query: str, num_results: int = 3, **kwargs) -> ToolOutput:
        """
        Simulate web search.
        
        Args:
            query: Search query
            num_results: Number of results to return
        """
        # Mock search results
        mock_results = [
            {
                "title": f"Result for '{query}' - Article {i+1}",
                "url": f"https://example.com/article-{i+1}",
                "snippet": f"This is a mock search result for query: {query}"
            }
            for i in range(num_results)
        ]
        
        return ToolOutput(
            success=True,
            result=mock_results,
            metadata={"query": query, "count": num_results}
        )


class TextProcessorTool(Tool):
    """Process and manipulate text strings"""
    
    @property
    def name(self) -> str:
        return "text_processor"
    
    @property
    def description(self) -> str:
        return "Processes text: count words, extract emails, convert case, etc."
    
    async def execute(self, text: str, operation: str = "word_count", **kwargs) -> ToolOutput:
        """
        Process text with specified operation.
        
        Args:
            text: Input text to process
            operation: Operation to perform (word_count, extract_emails, to_upper, to_lower)
        """
        try:
            if operation == "word_count":
                result = len(text.split())
            elif operation == "extract_emails":
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                result = re.findall(email_pattern, text)
            elif operation == "to_upper":
                result = text.upper()
            elif operation == "to_lower":
                result = text.lower()
            elif operation == "char_count":
                result = len(text)
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={"operation": operation, "input_length": len(text)}
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"Text processing error: {str(e)}"
            )


# Registry of built-in tools
BUILTIN_TOOLS = [
    CalculatorTool(),
    WebSearchTool(),
    TextProcessorTool()
]
