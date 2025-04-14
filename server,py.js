from mcp.server.fastmcp import FastMCP

mcp = FastMCP("DemoServer")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers and return the result."""
    return a + b

if __name__ == "__main__":
    mcp.run(transport="sse")  # or transport="sse" for HTTP Server-Sent Events