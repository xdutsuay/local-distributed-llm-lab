"""
Tests for tool execution framework
"""
import pytest
from coordinator.tools.base import Tool, ToolOutput
from coordinator.tools.builtin_tools import CalculatorTool, WebSearchTool, TextProcessorTool
from coordinator.tools.registry import ToolRegistry, get_tool_registry


@pytest.mark.asyncio
async def test_calculator_tool_basic():
    """Test calculator with simple expression"""
    calc = CalculatorTool()
    result = await calc.execute(expression="2 + 2")
    
    assert result.success is True
    assert result.result == 4
    assert result.error is None


@pytest.mark.asyncio
async def test_calculator_tool_complex():
    """Test calculator with complex expression"""
    calc = CalculatorTool()
    result = await calc.execute(expression="sqrt(16) + 2 * 3")
    
    assert result.success is True
    assert result.result == 10.0


@pytest.mark.asyncio
async def test_calculator_tool_math_functions():
    """Test calculator with math functions"""
    calc = CalculatorTool()
    result = await calc.execute(expression="sin(0)")
    
    assert result.success is True
    assert abs(result.result) < 0.0001  # sin(0) ≈ 0


@pytest.mark.asyncio
async def test_calculator_tool_invalid():
    """Test calculator rejects dangerous expressions"""
    calc = CalculatorTool()
    result = await calc.execute(expression="__import__('os').system('ls')")
    
    assert result.success is False
    assert "forbidden" in result.error.lower()


@pytest.mark.asyncio
async def test_web_search_tool():
    """Test web search returns mock results"""
    search = WebSearchTool()
    result = await search.execute(query="Python programming", num_results=2)
    
    assert result.success is True
    assert len(result.result) == 2
    assert all("title" in r and "url" in r for r in result.result)


@pytest.mark.asyncio
async def test_text_processor_word_count():
    """Test text processor word count"""
    processor = TextProcessorTool()
    result = await processor.execute(
        text="The quick brown fox jumps",
        operation="word_count"
    )
    
    assert result.success is True
    assert result.result == 5


@pytest.mark.asyncio
async def test_text_processor_extract_emails():
    """Test text processor email extraction"""
    processor = TextProcessorTool()
    result = await processor.execute(
        text="Contact us at hello@example.com or support@test.org",
        operation="extract_emails"
    )
    
    assert result.success is True
    assert len(result.result) == 2
    assert "hello@example.com" in result.result


def test_tool_registry_initialization():
    """Test tool registry auto-registers built-in tools"""
    registry = ToolRegistry()
    
    assert len(registry.tools) >= 3
    assert "calculator" in registry.tools
    assert "web_search" in registry.tools
    assert "text_processor" in registry.tools


@pytest.mark.asyncio
async def test_tool_registry_execute():
    """Test executing tool via registry"""
    registry = ToolRegistry()
    result = await registry.execute_tool("calculator", expression="5 * 5")
    
    assert result.success is True
    assert result.result == 25


@pytest.mark.asyncio
async def test_tool_registry_unknown_tool():
    """Test executing unknown tool returns error"""
    registry = ToolRegistry()
    result = await registry.execute_tool("nonexistent_tool", param="value")
    
    assert result.success is False
    assert "not found" in result.error


def test_tool_registry_stats():
    """Test tool usage statistics tracking"""
    registry = ToolRegistry()
    initial_count = registry.usage_stats.get("calculator", 0)
    
    # Execute tool (need to use asyncio.run for sync test)
    import asyncio
    asyncio.run(registry.execute_tool("calculator", expression="1 + 1"))
    
    assert registry.usage_stats["calculator"] == initial_count + 1


def test_global_registry_singleton():
    """Test get_tool_registry returns same instance"""
    registry1 = get_tool_registry()
    registry2 = get_tool_registry()
    
    assert registry1 is registry2
