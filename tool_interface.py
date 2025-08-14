"""
Abstract base class for all chatbot tools
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for all chatbot tools"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.enabled = True
    
    @abstractmethod
    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with given query and parameters
        
        Args:
            query: The user query or search term
            **kwargs: Additional parameters specific to the tool
            
        Returns:
            Dict containing:
                - success: bool indicating if execution was successful
                - result: The actual result data
                - message: Human-readable message
                - metadata: Additional information about the execution
        """
        pass
    
    @abstractmethod
    def is_relevant(self, query: str, context: Dict[str, Any] = None) -> bool:
        """
        Determine if this tool is relevant for the given query
        
        Args:
            query: The user query
            context: Additional context information
            
        Returns:
            bool: True if tool should be used for this query
        """
        pass
    
    def get_info(self) -> Dict[str, str]:
        """Get tool information"""
        return {
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled
        }
    
    def enable(self):
        """Enable the tool"""
        self.enabled = True
        logger.info(f"Tool {self.name} enabled")
    
    def disable(self):
        """Disable the tool"""
        self.enabled = False
        logger.info(f"Tool {self.name} disabled")


class ToolManager:
    """Manages all available tools for the chatbot"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        logger.info("ToolManager initialized")
    
    def register_tool(self, tool: BaseTool):
        """Register a new tool"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def unregister_tool(self, tool_name: str):
        """Unregister a tool"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
        else:
            logger.warning(f"Tool {tool_name} not found for unregistration")
    
    def get_relevant_tools(self, query: str, context: Dict[str, Any] = None) -> List[BaseTool]:
        """Get all tools that are relevant for the given query"""
        relevant_tools = []
        
        for tool in self.tools.values():
            if tool.enabled and tool.is_relevant(query, context):
                relevant_tools.append(tool)
        
        logger.info(f"Found {len(relevant_tools)} relevant tools for query: {query[:50]}...")
        return relevant_tools
    
    def execute_tool(self, tool_name: str, query: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific tool"""
        if tool_name not in self.tools:
            return {
                'success': False,
                'result': None,
                'message': f"Tool {tool_name} not found",
                'metadata': {}
            }
        
        tool = self.tools[tool_name]
        if not tool.enabled:
            return {
                'success': False,
                'result': None,
                'message': f"Tool {tool_name} is disabled",
                'metadata': {}
            }
        
        try:
            return tool.execute(query, **kwargs)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                'success': False,
                'result': None,
                'message': f"Error executing tool: {str(e)}",
                'metadata': {'error': str(e)}
            }
    
    def execute_relevant_tools(self, query: str, context: Dict[str, Any] = None, max_tools: int = None) -> List[Dict[str, Any]]:
        """Execute all relevant tools for a query"""
        relevant_tools = self.get_relevant_tools(query, context)
        
        if max_tools:
            relevant_tools = relevant_tools[:max_tools]
        
        results = []
        for tool in relevant_tools:
            logger.info(f"Executing tool: {tool.name}")
            result = self.execute_tool(tool.name, query)
            result['tool_name'] = tool.name
            results.append(result)
        
        return results
    
    def list_tools(self) -> List[Dict[str, str]]:
        """List all registered tools"""
        return [tool.get_info() for tool in self.tools.values()]
    
    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """Get a tool by its name"""
        return self.tools.get(name)
    
    def enable_tool(self, tool_name: str):
        """Enable a specific tool"""
        if tool_name in self.tools:
            self.tools[tool_name].enable()
        else:
            logger.warning(f"Tool {tool_name} not found")
    
    def disable_tool(self, tool_name: str):
        """Disable a specific tool"""
        if tool_name in self.tools:
            self.tools[tool_name].disable()
        else:
            logger.warning(f"Tool {tool_name} not found")
    
    def get_tools_summary(self) -> str:
        """Get a human-readable summary of all tools"""
        if not self.tools:
            return "No tools registered."
        
        summary = "Available Tools:\n"
        for tool in self.tools.values():
            status = "✓" if tool.enabled else "✗"
            summary += f"{status} {tool.name}: {tool.description}\n"
        
        return summary.strip()
