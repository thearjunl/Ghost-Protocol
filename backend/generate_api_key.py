#!/usr/bin/env python3
"""Generate a secure API key for GhostProtocol authentication."""

import secrets
import sys

def generate_api_key(length: int = 32) -> str:
    """Generate a cryptographically secure API key.
    
    Args:
        length: Number of bytes for the key (default 32 = 256 bits)
    
    Returns:
        URL-safe base64-encoded string
    """
    return secrets.token_urlsafe(length)


if __name__ == "__main__":
    print("=" * 60)
    print("GhostProtocol API Key Generator")
    print("=" * 60)
    print()
    
    # Generate key
    api_key = generate_api_key()
    
    print(f"Generated API Key:\n{api_key}\n")
    print("Add this to your .env file:")
    print(f"GHOSTPROTOCOL_API_KEY={api_key}")
    print()
    print("⚠️  Keep this key secure and never commit it to version control!")
    print("=" * 60)
