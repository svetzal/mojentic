from datetime import datetime
from mojentic.llm.tools.llm_tool import LLMTool


class CurrentDateTimeTool(LLMTool):
    def run(self, format_string: str = "%Y-%m-%d %H:%M:%S") -> dict:
        """
        Returns the current date and time.
        
        Parameters
        ----------
        format_string : str, optional
            The format string for the datetime, by default "%Y-%m-%d %H:%M:%S"
            
        Returns
        -------
        dict
            A dictionary containing the current date and time
        """
        current_time = datetime.now()
        formatted_time = current_time.strftime(format_string)
        
        return {
            "current_datetime": formatted_time,
            "timestamp": current_time.timestamp(),
            "timezone": datetime.now().astimezone().tzname()
        }
    
    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "get_current_datetime",
                "description": "Get the current date and time. Useful when you need to know the current time or date.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "format_string": {
                            "type": "string",
                            "description": "Format string for the datetime (e.g., '%Y-%m-%d %H:%M:%S', '%A, %B %d, %Y'). Default is ISO format."
                        }
                    },
                    "required": []
                }
            }
        }