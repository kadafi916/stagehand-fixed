import asyncio

from ..utils import load_plugins, invoke_plugins

plugins, broken_plugins = load_plugins('platform', ['win32'])

async def start(manager):
    """
    Called when the manager is starting.
    """
    await invoke_plugins(plugins, 'start', manager)



def stop():
    for plugin in plugins.values():
        if hasattr(plugin, 'stop'):
            plugin.stop()