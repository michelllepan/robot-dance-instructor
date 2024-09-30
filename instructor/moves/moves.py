from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Move:
    move_type: str
    replay_id: Optional[str] = None
    move_edits: Optional[List[str]] = field(default_factory=list)
    hand: Optional[str] = None
    object_to_take: Optional[str] = None
    magnitude: Optional[float] = None
    direction: Optional[str] = None
    
    def __post_init__(self):
        # Validate move_type
        valid_types = {'follow', 'take', 'free-space', 'replay', 'pointing'}
        if self.move_type not in valid_types:
            raise ValueError(f"Invalid move_type: {self.move_type}. Must be one of {valid_types}")
        
        # Validate parameters based on move_type
        if self.move_type == 'replay':
            if not self.replay_id or not isinstance(self.move_edits, list):
                raise ValueError("Replay mode requires a replay_id and a move_edits array")
        
        elif self.move_type == 'follow':
            if self.hand not in {'right-hand', 'left-hand'}:
                raise ValueError("Follow mode requires hand to be either 'right-hand' or 'left-hand'")
        
        elif self.move_type == 'take':
            if not isinstance(self.object_to_take, str):
                raise ValueError("Take mode requires an object to take as a string")
        
        elif self.move_type == 'free-space':
            if not isinstance(self.magnitude, (int, float)) or not isinstance(self.direction, str):
                raise ValueError("Free-space mode requires a magnitude (float/int) and a direction (str)")
        
        elif self.move_type == 'pointing':
            if not isinstance(self.magnitude, (int, float)):
                raise ValueError("Pointing mode requires a magnitude (float/int)")
    
    def execute(self):
        if self.move_type == 'replay':
            return self._execute_replay()
        elif self.move_type == 'follow':
            return self._execute_follow()
        elif self.move_type == 'take':
            return self._execute_take()
        elif self.move_type == 'free-space':
            return self._execute_free_space()
        elif self.move_type == 'pointing':
            return self._execute_pointing()

    def _execute_replay(self):
        # Execute logic for replay mode
        print(f"Replaying move with ID {self.replay_id} and edits {self.move_edits}")
        # Add your custom replay logic here
        return f"Replayed move {self.replay_id} with edits {self.move_edits}"
    
    def _execute_follow(self):
        # Execute logic for follow mode
        print(f"Following with {self.hand}")
        # Add your custom follow logic here
        return f"Following with {self.hand}"
    
    def _execute_take(self):
        # Execute logic for take mode
        print(f"Taking object: {self.object_to_take}")
        # Add your custom take logic here
        return f"Took {self.object_to_take}"
    
    def _execute_free_space(self):
        # Execute logic for free-space mode
        print(f"Moving {self.magnitude} units towards {self.direction}")
        # Add your custom free-space logic here
        return f"Moved {self.magnitude} units towards {self.direction}"
    
    def _execute_pointing(self):
        # Execute logic for pointing mode
        print(f"Pointing with magnitude {self.magnitude}")
        # Add your custom pointing logic here
        return f"Pointed with magnitude {self.magnitude}"

