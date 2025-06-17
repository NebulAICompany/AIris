import sys
import asyncio
import uvicorn

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the uvicorn server
        loop.run_until_complete(
            uvicorn.run(
                "aiiris_backend.app.main:app",
                host="127.0.0.1",
                port=8000,
                loop="none",  # Important: Let uvicorn use our loop
            )
        )
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            # Clean up pending tasks
            pending = asyncio.all_tasks(loop=loop)
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.close()
        except Exception as e:
            print(f"Error closing loop: {e}")
