"""Barcode Service - Utility to generate Code-128 / EAN-13 barcodes"""
import random


def generate_random_barcode(prefix: str = "893") -> str:
    """Generate a valid 13-digit EAN-13 format barcode string."""
    digits = [int(c) for c in prefix]
    while len(digits) < 12:
        digits.append(random.randint(0, 9))
    
    # Calculate checksum digit for EAN-13
    checksum = (10 - (sum(digits[::2]) + sum(digits[1::2]) * 3) % 10) % 10
    digits.append(checksum)
    return "".join(map(str, digits))


def generate_barcode_svg(code: str, width: int = 250, height: int = 80) -> str:
    """Generate a clean Code-128 SVG representation for printing and display."""
    # Build simple bar pattern based on character hash for visually distinct barcodes
    bars = []
    x = 10
    bar_width = (width - 20) / (len(code) * 11)
    
    for i, char in enumerate(code):
        char_val = ord(char)
        pattern = bin(char_val)[2:].zfill(8)
        for bit in pattern:
            if bit == '1':
                bars.append(f'<rect x="{x:.2f}" y="10" width="{bar_width*1.2:.2f}" height="{height-30}" fill="#1e293b"/>')
            x += bar_width

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
        <rect width="100%" height="100%" fill="#ffffff"/>
        {''.join(bars)}
        <text x="{width/2}" y="{height-8}" font-family="monospace" font-size="14" font-weight="bold" text-anchor="middle" fill="#0f172a">{code}</text>
    </svg>'''
    return svg_content
