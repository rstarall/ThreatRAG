
# 客户端代码用于连接服务器，并使用工具
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:    
    def __init__(self, url: str):
        self.url = url
        self.local_cmd_server_params = StdioServerParameters(
                                            command="python",
                                            args=["./mcp/server/main_server.py"])


    async def get_or_create_conversation(self, conversation_id: str) -> str:
        pass

    async def send_message(self, conversation_id: str, message: str) -> str:
        pass

    async def get_message(self, conversation_id: str) -> str:
        pass


