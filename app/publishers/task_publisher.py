from app.constants import TASK_NAME
from app.publishers.connectors import BaseConnector, PublishResult


class TaskPublisher:
    def __init__(self, connector: BaseConnector):
        self._connector = connector

    async def generate_tour_pdf(self, request: dict) -> PublishResult:
        return await self._connector.publish(
            queue="pdf", task_name=TASK_NAME, kwargs={"request_data": request}
        )
