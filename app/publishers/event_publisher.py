from app.publishers.connectors import RedisEventConnector


class EventPublisher:
    def __init__(self, connector: RedisEventConnector):
        self._connector = connector

    def task_ready(self, request_id: str, url: str):
        self._connector.publish_event(
            channel=f"task_updates:{request_id}",
            payload={"request_id": request_id, "status": "ready", "url": url},
        )

    def task_failed(self, request_id: str, reason: str):
        self._connector.publish_event(
            channel=f"task_updates:{request_id}",
            payload={"request_id": request_id, "status": "failed", "reason": reason},
        )
