"""Utility functions for formatting output.

This module provides utility functions for formatting console output in a consistent way.
"""

from colorama import init, Fore, Style

# Initialize colorama
init()

def format_block(content: str, separator: str = "#" * 39) -> str:
    """Format a block of text with separator lines for clear console output.

    Parameters
    ----------
    content : str
        The content to be formatted
    separator : str, optional
        The separator line to use, defaults to 39 '#' characters

    Returns
    -------
    str
        The formatted string with separator lines above and below the content
    """
    return f"\n\n{separator}\n{content}\n{separator}\n\n"


def print_green(text: str) -> None:
    """Print text in green color to the console.

    Parameters
    ----------
    text : str
        The text to be printed in green color
    """
    print(f"{Fore.GREEN}{text}{Style.RESET_ALL}")
