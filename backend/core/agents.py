from agents import Agent, Runner
from .tools.mcp import alpha_vantage_mcp_server
from .prompts import alpha_vantage_prompt
from .prompts import office_agent_prompt
from .tools.document import (
    create_excel_from_table,
    create_word_document,
)

alpha_vantage_agent = Agent(
    name="Alpha Vantage Finance Agent",
    instructions=alpha_vantage_prompt,
    mcp_servers=[alpha_vantage_mcp_server],
)


office_agent = Agent(
    name="office_agent",
    instructions=office_agent_prompt,
    tools=[
        create_excel_from_table,
        create_word_document,
    ],
)


async def main():
    await alpha_vantage_mcp_server.connect()
    result = await Runner.run(alpha_vantage_agent, "Tesla hisse senedi ne kadar  ")
    print(result)


# TODO: buradaki main fonksiyonu sadece connect hatırlatması için
