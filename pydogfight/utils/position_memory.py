from __future__ import annotations

from pydogfight.core.models import BoundingBox
import numpy as np

class PositionMemory:
    def __init__(self, boundary: BoundingBox, sep: int):
        self.boundary: BoundingBox = boundary
        self.sep = sep
        self.x_range = self.boundary.int_x_range
        self.y_range = self.boundary.int_y_range
        # memory 记录每个位置走了多少次
        self.memory: np.ndarray | None = None
        self.reset()

    def reset(self):
        x_range = self.boundary.int_x_range
        y_range = self.boundary.int_y_range

        num_x = int((x_range[1] - x_range[0]) / self.sep)
        num_y = int((y_range[1] - y_range[0]) / self.sep)

        self.memory = np.zeros((num_x + 1, num_y + 1), dtype=int)

    def add_position(self, position: tuple[float, float]):
        """
        add a position to the memory
        :param position: the position to add
        :return:
        """
        # 确定位置在memory中的索引
        position = self.boundary.limit(position)

        x_index = int((position[0] - self.x_range[0]) / self.sep)
        y_index = int((position[1] - self.y_range[0]) / self.sep)

        # 更新该位置的记忆
        self.memory[x_index, y_index] += 1

    def pick_position(self):
        """
        从记忆中随机提取出一个走的最少的点
        :return:
        """
        # 找到最小值的索引
        min_indices = np.argwhere(self.memory == np.min(self.memory))

        # 随机选择一个最小值的索引
        index = np.random.choice(len(min_indices))

        # 获取选择的位置
        selected_position = min_indices[index]

        return selected_position[0] * self.sep + self.x_range[0], selected_position[1] * self.sep + self.y_range[0]