from __future__ import annotations

import queue
import typing

import pybts

from pydogfight.policy.policy import Policy, AgentPolicy
from pydogfight.envs import Dogfight2dEnv, Aircraft
from abc import ABC


class BTPolicyNode(pybts.Action, ABC):
    """
    BT Policy Base Class Node
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_messages = queue.Queue(maxsize=20)  # update过程中的message

    @property
    def env(self) -> Dogfight2dEnv:
        return self.context['env']

    @property
    def agent_name(self) -> str:
        return self.context['agent_name']

    @property
    def agent(self) -> Aircraft | None:
        if self.env is None:
            return None
        return self.env.get_agent(self.agent_name)

    def put_update_message(self, msg: str):
        if self.update_messages.full():
            self.update_messages.get_nowait()
        msg = f"{self.debug_info['tick_count']}: {msg}"
        self.update_messages.put_nowait(msg)

    def to_data(self):
        return {
            **super().to_data(),
            'agent_name'     : self.agent_name,
            'update_messages': pybts.utility.read_queue_without_destroying(self.update_messages)
        }
