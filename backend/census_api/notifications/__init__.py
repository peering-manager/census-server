from .base import Notifier
from .discord import DiscordNotifier

_discord_notifier = DiscordNotifier()


def get_notifiers() -> list[Notifier]:
    return [_discord_notifier]


__all__ = ["Notifier", "get_notifiers"]
