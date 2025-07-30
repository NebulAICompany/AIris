from .agent_as_tools import office_agent_tool, alpha_vantage_tool
from .document import create_excel_from_table, create_word_document


document_tools = [create_excel_from_table, create_word_document]
rag_agent_as_tools = [office_agent_tool, alpha_vantage_tool]
