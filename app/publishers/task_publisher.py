from app.publishers.connectors import BaseConnector, PublishResult


class TaskPublisher:
    def __init__(self, connector: BaseConnector):
        self._connector = connector

    async def generate_tour_pdf(self, request: dict) -> PublishResult:
        return await self._connector.publish(
            queue="pdf", task_name="generate_tour_pdf", args=[request]
        )
