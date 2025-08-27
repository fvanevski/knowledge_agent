# utils.py

def format_bytes(byte_count):
    """
    Formats an integer of bytes into a human-readable string in B, KB, or MB.

    Args:
        byte_count: An integer representing the number of bytes.

    Returns:
        A string formatted as B, KB, or MB with commas and no decimal places.
    """
    if not isinstance(byte_count, int):
        raise TypeError("Input must be an integer.")

    if byte_count < 1024:
        # Format as Bytes if less than 1 KB
        return f"{byte_count:,} B"
    elif byte_count < 1024 * 1024:
        # Format as Kilobytes if less than 1 MB
        kb_value = round(byte_count / 1024)
        return f"{kb_value:,} KB"
    else:
        # Format as Megabytes for 1 MB or more
        mb_value = round(byte_count / (1024 * 1024))
        return f"{mb_value:,} MB"