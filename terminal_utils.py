# terminal_utils.py
import random

def print_colorful_break(text: str):
    """Prints a colorful horizontal break with a title."""
    colors = [
        "\033[91m",  # Red
        "\033[92m",  # Green
        "\033[93m",  # Yellow
        "\033[94m",  # Blue
        "\033[95m",  # Magenta
        "\033[96m",  # Cyan
    ]
    reset_color = "\033[0m"
    
    color = random.choice(colors)
    
    width = 80
    padding = (width - len(text) - 2)
    
    print(f"\n{color}{'=' * (padding // 2)} {text} {'=' * (padding - (padding // 2))}{reset_color}\n")

