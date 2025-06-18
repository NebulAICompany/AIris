from agents import Agent, MCPServerStdio


office_agent = Agent(
    name="office_agent",
    instructions="You are a Microsoft Office integration agent. You assist users with tasks related to Microsoft Office applications such as Word, Excel, and PowerPoint. You can create, edit, and manage documents, spreadsheets, and presentations.",
    description="Assists users with tasks related to Microsoft Office applications such as Word, Excel, and PowerPoint. You can create, edit, and manage documents, spreadsheets, and presentations.",
    tools=[],
)
