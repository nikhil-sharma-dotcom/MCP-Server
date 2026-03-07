class MCPToolError(Exception):
    def __init__(self, message: str, tool: str):
        super().__init__(message)
        self.tool = tool