from __future__ import annotations
from gym_dogfight.policy.policy import AgentPolicy
from gym_dogfight.envs.dogfight_2d_env import Dogfight2dEnv
from gym_dogfight.core.actions import Actions
from typing import List
import pygame


class ManualPolicy(AgentPolicy):

    def __init__(self, env: Dogfight2dEnv, control_agents: list[str] | None = None, delta_time: float = 0.01):
        super().__init__(env=env, agent_name=control_agents[0], delta_time=delta_time)
        self.control_index = 0
        self.control_agents = control_agents

    def execute(self, observation, delta_time: float):
        agent = self.env.get_agent(self.agent_name)
        self.env.render_info['duration'] = f'{self.env.time:.0f} s'
        self.env.render_info['agent'] = self.agent_name
        self.env.render_info['x'] = f'{agent.x:.0f}'
        self.env.render_info['y'] = f'{agent.y:.0f}'
        self.env.render_info['psi'] = f'{agent.psi:.0f}'
        self.env.render_info['fuel'] = f'{agent.fuel:.0f}'
        self.env.render_info['missile'] = f'{agent.missile_count}'
        self.env.render_info['destroy_enemy'] = f'{agent.missile_destroyed_agents}'

        self.env.render_info['actions'] = f'{agent.actions.qsize()}'

        event = pygame.event.poll()
        # if event.type == pygame.QUIT:
        #     self.env.close()
        #     return
        if event.type == pygame.KEYDOWN:
            print('KEYDOWN', self.last_time)
            event_key = pygame.key.name(int(event.key))
            if event_key == "escape":
                self.env.close()
                return
            if event_key == "backspace":
                self.env.reset()
                return
            if event.key == pygame.K_TAB:
                self.control_index = (self.control_index + 1) % len(self.control_agents)
                self.agent_name = self.control_agents[self.control_index]

            if event.key == pygame.K_SPACE:
                # 朝着最近的敌人发射导弹
                enemy = self.env.battle_area.find_nearest_enemy(self.agent_name)
                if enemy is not None:
                    self.actions.put_nowait([Actions.fire_missile, enemy.x, enemy.y])
        elif event.type == pygame.MOUSEBUTTONDOWN:
            print('MOUSEBUTTONDOWN', self.last_time)
            # 获取鼠标点击的位置
            from gym_dogfight.utils.rendering import screen_point_to_game_point
            position = screen_point_to_game_point(
                    screen_point=pygame.mouse.get_pos(),
                    game_size=self.env.options.game_size,
                    screen_size=self.env.options.screen_size
            )
            self.actions.put_nowait([Actions.go_to_location, position[0], position[1]])