from abc import ABC, abstractmethod; from dataclasses import dataclass

@dataclass
class PublishResult:
    success: bool
    platform: str
    message_id: str | None = None
    error_message: str | None = None


class SocialPublisher(ABC):
    platform: str

    @abstractmethod
    def publish(self, content: str) -> PublishResult:
        """
        Publish content
        """
        raise NotImplementedError