"""scan.py - utility module for barcode/product ID scanning.

This module is a placeholder and can be extended with hardware scanner integration.
It is required by the project request and provides a simple local API.
"""


def decode_product_id(raw_input: str) -> int:
    """Convert scanned text into product ID integer."""
    if not raw_input:
        raise ValueError("Empty scan input")
    text = raw_input.strip().split()[0]
    return int(text)


if __name__ == "__main__":
    print("scan.py is a helper module for HyperMarket Pro")
