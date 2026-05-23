import random
import enum
import math
from collections import defaultdict
from dataclasses import dataclass, field

GRID        = 10
TOWER       = (5, 5)
TOWER_RANGE = 3
WAVES       = 3

class EnemyType(enum.Enum):
    NORMAL   = "N"
    ARMORED  = "A"
    FAST     = "F"
    SPLITTER = "S"

ENEMY_PROPS = {
    EnemyType.NORMAL:   (1, 1.0),
    EnemyType.ARMORED:  (3, 0.5),
    EnemyType.FAST:     (1, 2.0),
    EnemyType.SPLITTER: (2, 1.0),
}

ENEMY_COLOR = {
    EnemyType.NORMAL:   (220, 40,  40),
    EnemyType.ARMORED:  (50,  80,  220),
    EnemyType.FAST:     (240, 230, 40),
    EnemyType.SPLITTER: (160, 30,  160),
}

SPAWN_WEIGHTS = [0.5, 0.2, 0.2, 0.1]


@dataclass
class Enemy:
    pos:    tuple
    hp:     int
    etype:  EnemyType
    speed:  float
    max_hp: int
    _acc:   float = field(default=0.0, repr=False)

    def move(self):
        self._acc += self.speed
        steps = int(self._acc)
        self._acc -= steps
        pos = self.pos
        for _ in range(steps):
            dx = TOWER[0] - pos[0]
            dy = TOWER[1] - pos[1]
            d  = math.hypot(dx, dy)
            if d == 0:
                break
            nx = max(0, min(GRID - 1, pos[0] + round(dx / d)))
            ny = max(0, min(GRID - 1, pos[1] + round(dy / d)))
            pos = (nx, ny)
        return Enemy(pos, self.hp, self.etype, self.speed, self.max_hp, self._acc)

    def take_damage(self, dmg=1):
        self.hp = max(0, self.hp - dmg)
        return self.hp > 0  # True = still alive

    def spawn_on_death(self):
        if self.etype == EnemyType.SPLITTER:
            hp, spd = ENEMY_PROPS[EnemyType.NORMAL]
            return [Enemy(self.pos, hp, EnemyType.NORMAL, spd, hp) for _ in range(2)]
        return []

    def at_tower(self):
        return self.pos == TOWER


def random_edge():
    side = random.randint(0, 3)
    n    = random.randint(0, GRID - 1)
    if side == 0: return (0,        n)
    if side == 1: return (GRID - 1, n)
    if side == 2: return (n,        0)
    return                (n,        GRID - 1)


def random_enemy():
    etype       = random.choices(list(EnemyType), weights=SPAWN_WEIGHTS)[0]
    max_hp, spd = ENEMY_PROPS[etype]
    return Enemy(random_edge(), max_hp, etype, spd, max_hp)


class TowerBrain:
    def __init__(self, alpha=0.1, gamma=0.9, epsilon=0.2):
        self.q       = defaultdict(lambda: defaultdict(float))
        self.alpha   = alpha
        self.gamma   = gamma
        self.epsilon = epsilon

    def _state(self, enemies):
        if not enemies:
            return (3, 0, 0)
        dists       = [math.hypot(e.pos[0]-TOWER[0], e.pos[1]-TOWER[1]) for e in enemies]
        near_bucket = min(int(min(dists)), 3)
        hp_bucket   = min(max(e.hp for e in enemies), 3)
        cnt_bucket  = min(len(enemies), 3)
        return (near_bucket, hp_bucket, cnt_bucket)

    def choose(self, state, candidates):
        if not candidates:
            return None, 0
        actions = {
            0: min(candidates, key=lambda e: math.hypot(e.pos[0]-TOWER[0], e.pos[1]-TOWER[1])),
            1: max(candidates, key=lambda e: e.hp),
            2: min(candidates, key=lambda e: e.hp),
            3: random.choice(candidates),
        }
        if random.random() < self.epsilon:
            a = random.randint(0, 3)
        else:
            a = max(actions, key=lambda a: self.q[state][a])
        return actions[a], a

    def update(self, state, action, reward, next_state):
        curr     = self.q[state][action]
        max_next = max(self.q[next_state].values(), default=0.0)
        self.q[state][action] = (1-self.alpha)*curr + self.alpha*(reward + self.gamma*max_next)

    @property
    def size(self):
        return len(self.q)


def simulate():
    brain       = TowerBrain()
    ticks       = []
    global_tick = 0

    for wave in range(1, WAVES + 1):
        enemies = [random_enemy() for _ in range(random.randint(2, 4))]

        while enemies:
            global_tick += 1
            enemies_pre = list(enemies)

            in_range   = [e for e in enemies
                          if math.hypot(e.pos[0]-TOWER[0], e.pos[1]-TOWER[1]) <= TOWER_RANGE]
            state      = brain._state(enemies)
            killed_obj = None
            action     = 0
            reward     = 0

            if in_range:
                target, action = brain.choose(state, in_range)
                if target is not None:
                    still_alive = target.take_damage()
                    if not still_alive:
                        killed_obj = target
                        spawned    = target.spawn_on_death()
                        enemies    = [e for e in enemies if e is not target]
                        enemies.extend(spawned)
                        reward = 1

            enemies_post_kill = list(enemies)
            enemies           = [e.move() for e in enemies]
            leaked            = [e for e in enemies if e.at_tower()]
            enemies           = [e for e in enemies if not e.at_tower()]
            if leaked:
                reward -= 5 * len(leaked)

            next_state = brain._state(enemies)
            brain.update(state, action, reward, next_state)

            ticks.append(dict(
                wave              = wave,
                tick              = global_tick,
                enemies_pre       = enemies_pre,
                killed            = killed_obj,
                enemies_post_kill = enemies_post_kill,
                enemies_final     = list(enemies),
                q_size            = brain.size,
                last_reward       = reward,
            ))

    return ticks


def main():
    for td in simulate():
        kill_str = (f"  killed {td['killed'].etype.value}@{td['killed'].pos}"
                    if td['killed'] else "")
        print(f"W{td['wave']} T{td['tick']:02d} | "
              f"enemies={len(td['enemies_final']):2d} | "
              f"q={td['q_size']:3d} | reward={td['last_reward']:+.0f}{kill_str}")


if __name__ == "__main__":
    main()
