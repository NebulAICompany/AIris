# from agents import Agent
# #from agents import MCPServerStdio
# from office_mcp import OfficeTool
# office_mcp = MCPServerStdio(
#     name="OfficeTool",
#     command=["uvx", "officemcp"],
#     description="Performs Microsoft Office operations via OfficeMCP server. Supports Excel, Word, PowerPoint actions."
# )

# #office_tool = OfficeTool()

# office_agent = Agent(
#     name="office_agent",
#     instructions="""You are a Microsoft Office integration agent.
# You assist users with tasks related to Microsoft Office applications such as Word, Excel, and PowerPoint.
# You can create, edit, and manage documents, spreadsheets, and presentations by calling the OfficeTool.""",
#     description="Assists users with tasks related to Microsoft Office apps using OfficeTool.",
#     tools=[office_mcp],  # ✅ added Office MCP tool here
# )

# import asyncio

# async def main():
#     agent = office_agent()
#     await agent.start()
#     apps = await agent.available_apps()
#     print("Detected Office apps:", apps)
#     await agent.shutdown()

# if __name__ == "__main__":
#     asyncio.run(main())