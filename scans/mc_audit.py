import asyncio

from msgraph import GraphServiceClient

from .utils import *


class SessionMC:
    def __init__(self, creds) -> None:
        self.sess = None
        self.assert_handler = AssertHandler()
        self.creds = creds

    def __str__(self) -> None:
        print(f"Session Microsoft")

    def create_session(self) -> bool:
        """
        This function initializes the Graph API access
        """
        scopes = ["SecurityEvents.Read.All", "User.Read"]
        self.graph_client = GraphServiceClient(credentials=self.creds, scopes=scopes)
        return True

    def check_session(self) -> bool:
        return self.graph_client is not None


class MCAudit:
    def __init__(self, session: SessionMC, debug: bool) -> None:
        self.assert_handler = AssertHandler()
        self.debug = debug
        self.session = session
        self.secure_score = None

    async def get_secure_score(self):
        return await self.session.graph_client.security.secure_scores.get()
