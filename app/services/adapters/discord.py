import os; from dotenv import load_dotenv; import requests; from app.services.adapters.base import (PublishResult, SocialPublisher,)

load_dotenv()
class DiscordPublisher(SocialPublisher):
    platform = "discord"

    def __init__(self):
        self.webhook_url = os.getenv(
            "DISCORD_WEBHOOK_URL"
        )

        if not self.webhook_url:
            raise RuntimeError(
                "DISCORD_WEBHOOK_URL environment variable "
                "is not configured."
            )

    def publish(self, content: str) -> PublishResult:
        try:
            response = requests.post(
                self.webhook_url,
                json={
                    "content": content,
                },
                timeout=10,
            )

            response.raise_for_status()

        except requests.exceptions.RequestException as error:
            return PublishResult(
                success=False,
                platform=self.platform,
                error_message=str(error),
            )

        return PublishResult(
            success=True,
            platform=self.platform,
        )