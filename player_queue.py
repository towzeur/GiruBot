from enum import Enum


class PlayerQueue:
    class Flag(Enum):
        SKIP = 1
        REPLAY = 2

    class Modifier(Enum):
        LOOP = 1
        LOOP_QUEUE = 2

    def __init__(self):
        self.close, self.open = [], []
        self.cursor = 0

        self.flag: PlayerQueue.Flag = None
        self.modifiers: list[PlayerQueue.Modifier] = []

    def __len__(self):
        return len(self.open)

    @property
    def waiting(self):
        return max(0, len(self.open) - 1)

    @property
    def head(self):
        return self.open[0] if self.open else None

    @property
    def tail(self):
        return self.open[-1] if self.open else None

    @property
    def current(self):
        try:
            return self.open[self.cursor]
        except IndexError:
            return None

    @property
    def duration(self) -> int:
        return sum([req.duration for req in self.open])

    # --------------------------------------------------------------------------

    def set_skip(self):
        self.flag = PlayerQueue.Flag.SKIP

    def set_replay(self):
        self.flag = PlayerQueue.Flag.REPLAY

    def unset_flag(self):
        self.flag = None

    # --------------------------------------------------------------------------

    def toggle_modifier(self, option: "PlayerQueue.Modifier"):
        enabled = option in self.modifiers
        if enabled:
            self.modifiers.remove(option)
        else:
            self.modifiers.append(option)
        return not enabled

    def toggle_loop(self):
        return self.toggle_modifier(PlayerQueue.Modifier.LOOP)

    def toggle_loopqueue(self):
        return self.toggle_modifier(PlayerQueue.Modifier.LOOP_QUEUE)

    @property
    def loop_enabled(self) -> bool:
        return PlayerQueue.Modifier.LOOP in self.modifiers

    @property
    def loopqueue_enabled(self) -> bool:
        return PlayerQueue.Modifier.LOOP_QUEUE in self.modifiers

    # --------------------------------------------------------------------------

    def next(self):
        # flags have a higher priority
        if self.flag is PlayerQueue.Flag.SKIP:
            self.dequeue(idx=self.cursor)
            return self.current
        elif self.flag is PlayerQueue.Flag.REPLAY:
            return self.current

        # optons have a lower priority
        if self.loop_enabled:
            return self.current
        elif self.loopqueue_enabled:
            self.cursor = (self.cursor + 1) % len(self.open)
            return self.current
        else:  # next song
            for _ in range(self.cursor + 1):
                self.dequeue(idx=0)
            self.cursor = 0
            return self.current

    def enqueue(self, elt, top=False):
        if top:
            self.open.insert(self.cursor + 1, elt)
        else:
            self.open.append(elt)

    def dequeue(self, idx=0) -> bool:
        try:
            elt = self.open.pop(idx)
        except IndexError:
            return False
        else:
            self.close.append(elt)
            return True

