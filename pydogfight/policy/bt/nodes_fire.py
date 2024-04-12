from __future__ import annotations
from pydogfight.policy.bt.common import *


class FireMissileAtNearestEnemy(BTPolicyNode):
    """
    行为节点: 朝着最近的敌机发射导弹
    - SUCCESS: 发射导弹成功
    - FAILURE: 发射导弹失败（可能是没有发现最近敌机、剩余导弹为空、无法攻击到敌机）
    """

    def update(self) -> Status:
        if self.env.time - self.agent.last_fire_missile_time < self.env.options.aircraft_fire_missile_interval:
            # 发射时间间隔太短
            return Status.FAILURE

        if self.agent.missile_count <= 0:
            # self.put_update_message('Missile Count == 0')
            return Status.FAILURE

        enemy = self.env.battle_area.find_nearest_enemy(
                agent_name=self.agent_name,
                ignore_radar=False)

        if enemy is None:
            # self.put_update_message('No nearest enemy')
            return Status.FAILURE

        hit_point = self.agent.predict_missile_intercept_point(target_wpt=enemy.waypoint, target_speed=enemy.speed)
        if hit_point is None:
            # self.put_update_message('hit point is none')
            return Status.FAILURE

        if hit_point.time <= 0.9 * self.env.options.missile_flight_duration():
            # 有可能命中敌机
            self.actions.put_nowait((Actions.fire_missile, enemy.waypoint.x, enemy.waypoint.y))
            return Status.SUCCESS
        else:
            # self.put_update_message(f'没办法命中敌机 fire missile {enemy.waypoint} hit_point_time={hit_point.time}')
            return Status.FAILURE
