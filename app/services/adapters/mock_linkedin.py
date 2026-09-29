from app.services.adapters.base import (
    PublishResult,
    SocialPublisher,
)


class MockLinkedInPublisher(SocialPublisher):
    platform = "linkedin"

    def __init__(self):
        self.published_posts = []

    def publish(self, content: str) -> PublishResult:
        self.published_posts.append(content)

        return PublishResult(
            success=True,
            platform=self.platform,
            message_id=(
                f"mock-linkedin-"
                f"{len(self.published_posts)}"
            ),
        )