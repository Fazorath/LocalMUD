from __future__ import annotations


TIME_SLICES = ["morning", "afternoon", "evening", "night"]


class GameState:
    def __init__(self) -> None:
        self.turn_count = 0
        self.time_of_day = TIME_SLICES[0]
        self.highstorm_warning_active = False
        self._time_index = 0

    def advance_turn(self) -> None:
        self.turn_count += 1

    def maybe_change_time_of_day(self) -> bool:
        if self.turn_count == 0:
            return False
        if self.turn_count % 4 == 0:
            self._time_index = (self._time_index + 1) % len(TIME_SLICES)
            self.time_of_day = TIME_SLICES[self._time_index]
            if self.time_of_day == "morning":
                self.highstorm_warning_active = False
            return True
        return False

