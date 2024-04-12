from __future__ import annotations

import typing
from typing import Any, Optional, SupportsFloat, Tuple, Union

import gymnasium as gym
import numpy as np
from gymnasium.core import ActType, ObsType
from gymnasium.error import DependencyNotInstalled
from pydogfight.core.world_obj import *
from pydogfight.core.options import Options
from pydogfight.core.battle_area import BattleArea
from pydogfight.core.actions import Actions
import time
import threading
import asyncio
from pydogfight.utils.obs_utils import ObsUtils


class Dogfight2dEnv(gym.Env):
    metadata = {
        'render.modes': ['human', 'rgb_array'],
        # "render_fps"  : 50,
    }

    def __init__(self,
                 options: Options = Options(),
                 render_mode: str | None = None):
        super().__init__()
        options.validate()
        self.render_mode = render_mode
        self.options = options
        self.battle_area = BattleArea(options=options, render_mode=self.render_mode)
        self.obs_utils = ObsUtils(battle_area=self.battle_area)

        # (action_type, x, y)
        self.action_space_low = np.array([0, -options.game_size[1] / 2, -options.game_size[1] / 2])
        self.action_space_high = np.array([len(Actions), -options.game_size[1] / 2, -options.game_size[1] / 2])

        self.action_space = gym.spaces.Box(
                low=np.tile([0, -int(options.game_size[0] / 2), -int(options.game_size[1] / 2)],
                            (len(options.agents()), 1)),
                high=np.tile([len(Actions), int(options.game_size[0] / 2), int(options.game_size[1] / 2)],
                             (len(options.agents()), 1)),
                shape=(len(self.options.agents()), 3),
                dtype=np.int32)

        self.agent_action_space = gym.spaces.Box(
                low=np.array([-1, -1, -1]),
                high=np.array([1, 1, 1]),
                shape=(3,),
        )

        # type, color, destroyed, x, y, psi, speed, missile_count, fuel, radar_radius
        # self.observation_space = gym.spaces.Box(
        #         low=-options.game_size[0] / 2,
        #         high=options.game_size[0] / 2,
        #         shape=(len(options.agents()) + 3 + 7, 11),  # 最多同时记录所有飞机、基地、牛眼和7个导弹的信息
        #         dtype=np.float32)
        self.observation_space = self.obs_utils.observation_space
        # type, is_enemy, destroyed, r, theta, psi, speed, missile_count, fuel, radar_radius
        self.agent_observation_space = self.obs_utils.observation_space

        self.screen = None
        # self.clock # pygame.time.Clock
        self.isopen = True
        self.paused = False  # 是否暂停

        self.last_render_time = 0
        self.last_update_time = 0
        self.step_count = 0

        self.render_info = { }  # 渲染在屏幕上的信息

        self.game_info = {
            'red_wins'        : 0,
            'blue_wins'       : 0,
            'draws'           : 0,  # 平局几次
            'round'           : 0,  # 第几轮
            'truncated_count' : 0,
            'terminated_count': 0,
        }  # 游戏对战累积数据，在reset的时候更新
        # TODO 敌人的heatmap

        # 回调函数
        self.before_update_handlers: list[typing.Callable[['Dogfight2dEnv'], None]] = []
        self.after_update_handlers: list[typing.Callable[['Dogfight2dEnv'], None]] = []
        self.before_reset_handlers: list[typing.Callable[['Dogfight2dEnv'], None]] = []
        self.after_reset_handlers: list[typing.Callable[['Dogfight2dEnv'], None]] = []

    def add_before_update_handler(self, handler: typing.Callable[['Dogfight2dEnv'], None]):
        self.before_update_handlers.append(handler)

    def add_after_update_handler(self, handler: typing.Callable[['Dogfight2dEnv'], None]):
        self.after_update_handlers.append(handler)

    def add_before_reset_handler(self, handler: typing.Callable[['Dogfight2dEnv'], None]):
        self.before_reset_handlers.append(handler)

    def add_after_reset_handler(self, handler: typing.Callable[['Dogfight2dEnv'], None]):
        self.after_reset_handlers.append(handler)

    @property
    def time(self):
        return self.battle_area.time

    def get_agent(self, name) -> Aircraft:
        obj = self.battle_area.get_obj(name)
        assert isinstance(obj, Aircraft)
        return obj

    def reset(
            self,
            *,
            seed: int | None = None,
            options: dict[str, Any] | None = None,
    ) -> tuple[ObsType, dict[str, Any]]:
        for handler in self.before_reset_handlers:
            handler(self)

        info = self.gen_info()
        if info['winner'] == 'red':
            self.game_info['red_wins'] += 1
        elif info['winner'] == 'blue':
            self.game_info['blue_wins'] += 1
        elif info['winner'] == 'draw':
            self.game_info['draws'] += 1

        if info['truncated']:
            self.game_info['truncated_count'] += 1
        if info['terminated']:
            self.game_info['terminated_count'] += 1

        self.game_info['round'] += 1

        super().reset(seed=seed)

        self.step_count = 0

        self.battle_area.reset()

        if self.render_mode == "human":
            import pygame
            if self.screen is None:
                pygame.init()
                pygame.display.init()
                self.screen = pygame.display.set_mode(
                        self.options.screen_size,
                        pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
                self.screen.fill((255, 255, 255))
                pygame.display.set_caption("dogfight")
            # if self.clock is None:
            #     self.clock = pygame.time.Clock()
            self.render()

        for handler in self.after_reset_handlers:
            handler(self)

        return self.gen_obs(), self.gen_info()

    def gen_obs(self):
        if self.options.self_side == 'red':
            return self.obs_utils.gen_obs(agent_name=self.options.red_agents[0])
        else:
            return self.obs_utils.gen_obs(agent_name=self.options.blue_agents[0])

    def gen_agent_obs(self, agent_name: str):
        """
        获取agent视角的obs
        注意这里的坐标用相对极坐标来表示
        :param agent_name:
        :return:
        """
        return self.obs_utils.gen_obs(agent_name=agent_name)

    def gen_info(self) -> dict:
        info = {
            'truncated'   : self.time >= self.options.max_duration,
            'terminated'  : self.battle_area.winner != '',
            'winner'      : self.battle_area.winner,
            'time'        : self.time,
            'remain_count': self.battle_area.remain_count,
            'red_reward'  : self.gen_reward(color='red', previous=0),
            'blue_reward' : self.gen_reward(color='blue', previous=0)
        }
        return info

    def empty_action(self):
        return np.zeros(self.action_space.shape)

    def put_action(self, action):
        for i, act in enumerate(action):
            if act[0] == 0:
                continue
            agent_name = self.options.agents()[i]
            agent = self.battle_area.get_obj(agent_name)
            agent.put_action(act)

    def update(self):
        for handler in self.before_update_handlers:
            handler(self)
        next_time = self.battle_area.time + self.options.update_interval
        while self.battle_area.time < next_time:
            self.battle_area.update()
        if self.render_mode == 'human':
            self.last_update_time = time.time()
        for handler in self.after_update_handlers:
            handler(self)

    # async def agent_step(self, agent_name: str, action: list | np.ndarray | tuple[float, float, float]):
    #     old_info = self.gen_info()
    #     agent = self.get_agent(agent_name)
    #     agent.put_action(action)
    #     info = self.gen_info()
    #     reward = self.gen_reward(color=agent.color, previous=old_info)
    #     return self.gen_obs(), reward, info['terminated'], info['truncated'], info

    def step(
            self, action: ActType
    ) -> tuple[ObsType, SupportsFloat, bool, bool, dict[str, Any]]:
        """
        obs, reward, terminated, truncated, info = env.step(action)
        :param action: 所有动作
        :return:
        """
        self.step_count += 1
        self.put_action(action)
        old_info = self.gen_info()
        self.update()  # 更新环境
        info = self.gen_info()
        reward = self.gen_reward(color=self.options.self_side, previous=old_info)
        # 注意这里返回的状态是更新动作之前的（想获取更新动作之后的状态需要手动调用update）
        return self.gen_obs(), reward, info['terminated'], info['truncated'], info

    def render(self):
        try:
            import pygame
            from pygame import gfxdraw
        except ImportError as e:
            raise DependencyNotInstalled(
                    "pygame is not installed, run `pip install gymnasium[classic-control]`"
            ) from e
        # print(f'Render {self.duration} {self.last_render_time}')
        self.last_render_time = time.time()

        if self.render_mode == "human":
            self.screen.fill((255, 255, 255))

            play_pause_img = pygame_load_img('play.svg' if self.paused else 'pause.svg').convert_alpha()
            play_pause_img_rect = play_pause_img.get_rect()
            play_pause_img_rect.right = self.options.screen_size[0] - 10
            play_pause_img_rect.top = 10

            event = pygame.event.poll()
            if event is not None:
                if event.type == pygame.VIDEORESIZE:
                    self.options.screen_size = event.size
                    # 调整尺寸
                # 检测鼠标点击
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if play_pause_img_rect.collidepoint(event.pos):
                        self.paused = not self.paused  # 切换暂停状态

            render_info_y = 10
            for key in self.render_info:
                # 渲染文本到 Surface 对象
                render_text(
                        screen=self.screen,
                        text=f'{key}: {self.render_info[key]}',
                        topleft=(10, render_info_y),
                        text_size=18,
                )
                render_info_y += 20

            # 渲染安全区域
            # render_rect(self.options, screen=self.screen, rect=self.options.safe_boundary, color='grey')
            self.screen.blit(play_pause_img, play_pause_img_rect)
            self.battle_area.render(self.screen)
            pygame.event.pump()
            # self.clock.tick(self.options.render_fps)
            pygame.display.update()

    def should_render(self):
        if self.render_mode == 'human':
            time_passed = time.time() - self.last_render_time
            # print('should_render', time_passed, 'seconds')
            return time_passed >= (1 / self.options.render_fps)
        else:
            return False

    def should_update(self):
        if self.paused:
            return
        if self.render_mode == 'human':
            time_passed = (time.time() - self.last_update_time) * self.options.simulation_rate
            # print('should_update', time_passed, 'seconds')
            return time_passed >= self.options.update_interval
        else:
            return True

    def close(self):
        if self.screen is not None:
            import pygame

            pygame.display.quit()
            pygame.quit()
            self.isopen = False

    def gen_reward(self, color: str, previous: dict | float | None):
        """
        生成某方的累积奖励
        Args:
            color:
            previous: 之前的奖励/info，填0代表返回累积奖励
        Returns:
        """
        reward = self.options.step_reward * self.time  # 时间惩罚
        winner = self.battle_area.winner
        if winner != '':
            # 某一方获胜了
            if winner == color:
                reward += self.options.win_reward
            elif winner == 'draw':
                reward += self.options.draw_reward
            else:
                reward += self.options.lose_reward
        if previous is None:
            previous = 0
        if isinstance(previous, dict):
            previous = previous[f'{color}_reward']
        return reward - previous
