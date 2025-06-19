# import asyncio
# from agents import Agent, Runner
# from agents.tool import WebSearchTool

# def web_search_agent():
#     """
#     Returns an Agent equipped with WebSearchTool.
#     """
#     agent = Agent(
#         name="WebSearchAgent",
#         instructions=(
#             "You are WebSearchAgent. "
#             "When given a search query, perform a web search using WebSearchTool "
#             "and return a concise answer with citations."
#         ),
#         tools=[WebSearchTool()]
#     )
#     return agent

# async def test_search(query: str):
#     """
#     Runs the WebSearchAgent on a given query and prints the result.
#     """
#     agent = web_search_agent()
#     print(f"🔍 Testing web search with query: {query}\n")
#     response = await Runner.run(agent, query)
#     print("===== Agent Response =====")
#     print(response)

# if __name__ == "__main__":
#     sample_query = "Dolar kuru hakkında güncel bilgi ver"
#     asyncio.run(test_search(sample_query))
