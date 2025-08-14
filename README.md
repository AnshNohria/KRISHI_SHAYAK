# 🌾 Modern Agriculture Schemes Chatbot

A clean, modular chatbot architecture for helping farmers find relevant government agriculture schemes in India. Built with tool-based architecture for easy extensibility.

## 🏗️ Architecture Overview

### Core Components

1. **Data Processor** (`data_processor.py`)
   - Loads and processes Excel data with 534+ agriculture schemes
   - Cleans and structures scheme information
   - Extracts key fields: title, benefits, eligibility, application process, etc.

2. **Vector Database** (`database.py`)
   - Uses ChromaDB for semantic search capabilities
   - Stores scheme data as searchable vectors
   - Supports filtering by state, category, ministry

3. **Tool Interface** (`tool_interface.py`)
   - Abstract base class for all tools
   - Tool Manager for orchestrating multiple tools
   - Automatic tool selection based on query relevance

4. **Scheme Search Tool** (`scheme_search_tool.py`)
   - Implements the tool interface
   - Intelligent query optimization
   - Formatted, farmer-friendly responses

5. **Modern Chatbot** (`modern_chatbot.py`)
   - Main orchestrator using Google Gemini API
   - Automatic tool selection and execution
   - Contextual conversation handling

## 🚀 Key Features

### ✅ Current Capabilities
- **Semantic Search**: Find relevant schemes using natural language queries
- **Intelligent Tool Selection**: Automatically chooses appropriate tools based on query
- **Comprehensive Database**: 534+ schemes with detailed information
- **Farmer-Friendly Responses**: Clear, structured answers with actionable information
- **State-Specific Filtering**: Search schemes by state or ministry
- **Conversation Memory**: Maintains context across multiple exchanges

### 🔧 Extensible Architecture
- **Easy Tool Addition**: Add new tools by implementing `BaseTool` interface
- **Modular Design**: Each component is independent and testable
- **Clean Interfaces**: Well-defined APIs between components
- **Logging**: Comprehensive logging throughout the system

## � Database Statistics

- **Total Schemes**: 534 agriculture schemes
- **Data Source**: Excel file with 93 columns of detailed scheme information
- **Storage**: ChromaDB vector database for semantic search
- **Categories**: Various categories including crop insurance, financial assistance, irrigation, etc.
- **Coverage**: Multiple states and central government schemes

## 🛠️ Technical Stack

- **Python 3.8+**
- **ChromaDB**: Vector database for semantic search
- **Google Generative AI (Gemini)**: Large language model for responses
- **Pandas & OpenPyXL**: Excel data processing
- **Type Hints**: Full type annotation for better code quality

## 🏃‍♂️ Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Keys**:
   Update `config.py` with your Google Gemini API key

3. **Run the Chatbot**:
   ```bash
   python modern_chatbot.py
   ```

## 🧪 Testing Individual Components

### Test Data Processor:
```bash
python data_processor.py
```

### Test Database:
```bash
python database.py
```

### Test Scheme Search Tool:
```bash
python scheme_search_tool.py
```

## 📝 Usage Examples

### Basic Queries:
- "I need financial assistance for my farm"
- "What crop insurance schemes are available?"
- "How can I get a loan for irrigation equipment?"
- "PM-KISAN scheme details"

### State-Specific Queries:
- "Maharashtra irrigation schemes"
- "Gujarat subsidy programs"
- "Tamil Nadu farmer assistance"

### Category-Specific Queries:
- "Organic farming support"
- "Livestock insurance schemes"
- "Equipment subsidy programs"

## 🔧 Adding New Tools

1. **Create Tool Class**:
```python
from tool_interface import BaseTool

class NewTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="new_tool",
            description="Description of what this tool does"
        )
    
    def is_relevant(self, query: str, context=None) -> bool:
        # Logic to determine if tool should be used
        return "keyword" in query.lower()
    
    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        # Tool implementation
        return {
            'success': True,
            'result': "Tool result",
            'message': "Success message",
            'metadata': {}
        }
```

2. **Register Tool**:
```python
# In modern_chatbot.py setup_tools() method
new_tool = NewTool()
self.tool_manager.register_tool(new_tool)
```

## � Project Structure

```
agrihack/
├── modern_chatbot.py          # Main chatbot application
├── data_processor.py          # Excel data processing
├── database.py                # ChromaDB vector database
├── tool_interface.py          # Tool architecture framework
├── scheme_search_tool.py      # Scheme search implementation
├── config.py                  # Configuration settings
├── requirements.txt           # Python dependencies
├── myscheme-gov-in-2025-08-10.xlsx  # Source data
└── chroma_db/                 # Vector database storage
```

## 🎯 Future Enhancements

### Planned Tools:
- **Weather Tool**: Agricultural weather information
- **Market Price Tool**: Crop price information
- **Document Helper Tool**: Application form assistance
- **Contact Information Tool**: Government office contacts
- **FAQ Tool**: Common questions and answers

### Architecture Improvements:
- **Tool Caching**: Cache tool results for better performance
- **User Profiles**: Personalized recommendations based on user history
- **Multi-language Support**: Hindi and regional language support
- **Voice Interface**: Speech-to-text and text-to-speech capabilities

## 🤝 Contributing

To add new tools or enhance existing functionality:

1. Follow the established architecture patterns
2. Implement proper error handling and logging
3. Add type hints for better code quality
4. Create comprehensive tests
5. Update documentation

## � License

This project is designed to help farmers access government schemes and support agricultural development in India.

---

**Built with ❤️ for Indian farmers** 🇮🇳🌾
