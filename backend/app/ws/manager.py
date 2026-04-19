from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict

from fastapi import WebSocket


@dataclass
class WsClient:
    user_id: int
    socket: WebSocket


class TaskChatWsManager:
    def __init__(self) -> None:
        self._clients: DefaultDict[int, list[WsClient]] = defaultdict(list)

    async def connect(self, task_id: int, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients[task_id].append(WsClient(user_id=user_id, socket=websocket))

    def disconnect(self, task_id: int, websocket: WebSocket) -> None:
        clients = self._clients.get(task_id, [])
        self._clients[task_id] = [client for client in clients if client.socket is not websocket]
        if not self._clients[task_id]:
            self._clients.pop(task_id, None)

    async def broadcast(self, task_id: int, payload: dict) -> None:
        clients = self._clients.get(task_id, [])
        dead: list[WebSocket] = []
        for client in clients:
            try:
                await client.socket.send_json(payload)
            except Exception:
                dead.append(client.socket)
        for sock in dead:
            self.disconnect(task_id, sock)


class UserNotificationWsManager:
    def __init__(self) -> None:
        self._clients: DefaultDict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients[user_id].append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        clients = self._clients.get(user_id, [])
        self._clients[user_id] = [sock for sock in clients if sock is not websocket]
        if not self._clients[user_id]:
            self._clients.pop(user_id, None)

    async def send_to_user(self, user_id: int, payload: dict) -> None:
        clients = self._clients.get(user_id, [])
        dead: list[WebSocket] = []
        for socket in clients:
            try:
                await socket.send_json(payload)
            except Exception:
                dead.append(socket)
        for sock in dead:
            self.disconnect(user_id, sock)


task_chat_ws_manager = TaskChatWsManager()
user_notification_ws_manager = UserNotificationWsManager()
