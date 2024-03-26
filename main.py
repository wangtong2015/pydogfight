import math
import time

import gym_dogfight
import gymnasium as gym
import pygame
from gym_dogfight import Options, Dogfight2dEnv
from gym_dogfight.manual_control import ManualControl

# Use the parameter env_id to make the environment
# env = gym.make(env_id, render_mode='human')
# env = gym.make('Dogfight-v0', render_mode="human")  # for visual debugging

if __name__ == '__main__':
    options = Options()
    env = Dogfight2dEnv(options=options, render_mode='human')
    env.reset()
    manual_control = ManualControl(env, seed=0)
    manual_control.start()