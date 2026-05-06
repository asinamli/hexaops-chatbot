# çağrıyı alıp gerçek fonksiyonu çalıştıran  yeri olşşturalım

from app.schemas.tools import ToolCall, ToolResult

from app.tools.weather_tools import weather_tool
from app.tools.company_tools import company_info_tool
from app.tools.math_tools import (
    add_numbers,
    subtract_numbers,
    multiply_numbers,
    divide_numbers,
)

TOOL_MAP = {
    "weather_tool": weather_tool,
    "company_info_tool": company_info_tool,
    "add_numbers": add_numbers,
    "subtract_numbers": subtract_numbers,
    "multiply_numbers": multiply_numbers,
    "divide_numbers": divide_numbers,
}

def execute_tool(tool_call: ToolCall) -> ToolResult:
    tool_name = tool_call.name


    if tool_name not in TOOL_MAP:
        return ToolResult(
            name = tool_name,
            output = "bilinmeyen tool çağrısı"

        )
    
    selected_tool = TOOL_MAP[tool_name]

    try:
        result = selected_tool(**tool_call.arguments)

        return ToolResult(
            name=tool_name,
            output=str(result)
        )

    except Exception as e:
        return ToolResult(
            name=tool_name,
            output=f"Tool çalışırken hata oluştu: {e}"
        )