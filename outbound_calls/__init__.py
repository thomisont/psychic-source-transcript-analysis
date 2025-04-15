"""
Outbound Call Service using ElevenLabs MCP for voice calling.
"""

from .mcp_client import OutboundCallClient
from .app import app

__all__ = ["OutboundCallClient", "app"] 