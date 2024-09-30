import abc
import asyncio
import re
import xml.parsers.expat
import xml.parsers.expat
from typing import TypeVar

from instructor.moves.moves import Move


class RuntimeSession(abc.ABC):
    pass


RuntimeSessionObject = TypeVar('RuntimeSessionObject', bound=RuntimeSession)


class Runtime(abc.ABC):
    @abc.abstractmethod
    async def start_session(self) -> RuntimeSessionObject:
        pass

    @abc.abstractmethod
    async def define_replay_move(self, session: RuntimeSessionObject, move_id: str, start_time: float, stop_time: float):
        pass

    @abc.abstractmethod
    async def define_follow_move(self, session: RuntimeSessionObject, hand: str, duration: float):
        pass

    @abc.abstractmethod
    async def define_take_move(self, session: RuntimeSessionObject, object_to_take: str):
        pass

    @abc.abstractmethod
    async def define_free_space_move(self, session: RuntimeSessionObject, magnitude: float, direction: str):
        pass

    @abc.abstractmethod
    async def define_point_move(self, session: RuntimeSessionObject, magnitude: float):
        pass

    @abc.abstractmethod
    async def do_move(self, session: RuntimeSessionObject, move_id: str):
        pass

    @abc.abstractmethod
    async def speech(self, session: RuntimeSessionObject, speech: str):
        pass

    @abc.abstractmethod
    async def end_session(self, session: RuntimeSessionObject):
        pass


class Engine:
    def __init__(self, runtime: Runtime):
        self.runtime = runtime
        self.parser = xml.parsers.expat.ParserCreate()
        self.parser.Parse("<root>", False)  # give it a root element so that it won't end the document
        self.parser.StartElementHandler = self.start_element
        self.parser.EndElementHandler = self.end_element
        self.parser.CharacterDataHandler = self.char_data
        self.current_element = None
        self.current_data = ""
        self.move_stack = []
        self.execute_session = None
        self.tasks = []
        self.current_move_type = None
        self.current_move_params = {}
        self.current_move_start_time = None
        self.current_move_stop_time = None

    async def execute(self, parsed_sentence: str):
        self.execute_session = await self.runtime.start_session()
        self.tasks = []
        try:
            self.parser.Parse(parsed_sentence.strip(), False)
        except Exception as e:
            print(e)
            print("\n")
        print("finished parsing")
        await asyncio.gather(*self.tasks)
        await self.runtime.end_session(self.execute_session)

    def start_element(self, name, attrs):
        self.current_element = name
        
        if name == "move":
            # Extract move type and initialize move parameters
            self.current_move_type = attrs.get("type")
            self.current_move_params = {}
            self.current_move_start_time = None
            self.current_move_stop_time = None
            move = None  # Initialize move variable to store the Move object

            # Validate move type and initialize parameters accordingly
            if self.current_move_type == "replay":
                # Replay requires an ID and start/stop times
                self.current_move_id = attrs.get("id")
                if not self.current_move_id:
                    raise ValueError("Replay move must have an 'id' attribute.")
                move = Move(
                    move_type="replay",
                    replay_id=self.current_move_id,
                    start_time=self.current_move_start_time,
                    stop_time=self.current_move_stop_time
                )
            
            elif self.current_move_type == "follow":
                # Follow requires 'hand' and 'duration'
                self.current_move_params['hand'] = attrs.get("hand")
                self.current_move_params['duration'] = float(attrs.get("duration", 0))
                if not self.current_move_params['hand']:
                    raise ValueError("Follow move must have a 'hand' attribute.")
                move = Move(
                    move_type="follow",
                    hand=self.current_move_params['hand'],
                    duration=self.current_move_params['duration']
                )

            elif self.current_move_type == "take":
                # Take requires 'object_to_take'
                self.current_move_params['object_to_take'] = attrs.get("object")
                if not self.current_move_params['object_to_take']:
                    raise ValueError("Take move must have an 'object' attribute.")
                move = Move(
                    move_type="take",
                    object_to_take=self.current_move_params['object_to_take']
                )

            elif self.current_move_type == "free-space":
                # Free-space requires 'magnitude' and 'direction'
                self.current_move_params['magnitude'] = float(attrs.get("magnitude", 0))
                self.current_move_params['direction'] = attrs.get("direction")
                if not self.current_move_params['direction']:
                    raise ValueError("Free-space move must have a 'direction' attribute.")
                move = Move(
                    move_type="free-space",
                    magnitude=self.current_move_params['magnitude'],
                    direction=self.current_move_params['direction']
                )

            elif self.current_move_type == "pointing":
                # Pointing requires 'magnitude'
                self.current_move_params['magnitude'] = float(attrs.get("magnitude", 0))
                move = Move(
                    move_type="pointing",
                    magnitude=self.current_move_params['magnitude']
                )

            else:
                # Invalid move type
                raise ValueError(f"Invalid move type: {self.current_move_type}. Expected one of ['replay', 'follow', 'take', 'free-space', 'pointing'].")

            # Append the task to execute the move using the Move object
            self.tasks.append(self.runtime.do_move(self.execute_session, move))
        
        elif name == "word" and self.current_move_type == "replay":
            # Record the start and stop times for replay moves
            start_time = float(attrs["start"])
            stop_time = float(attrs["end"])
            if self.current_move_start_time is None or start_time < self.current_move_start_time:
                self.current_move_start_time = start_time
            if self.current_move_stop_time is None or stop_time > self.current_move_stop_time:
                self.current_move_stop_time = stop_time

        elif name == "response":
        # Handle command-based responses
            if "command" in attrs:
                command = attrs["command"]
                move_commands = command.split(';')
                for move_command in move_commands:
                    if move_command.strip():
                        # Use conversation parsing to convert to Move object
                        move_obj = self.conversation.parse_command(move_command.strip())
                        self.tasks.append(self.runtime.do_move(self.execute_session, move_obj))
        elif "speech" in attrs:
            self.tasks.append(self.runtime.speech(self.execute_session, attrs["speech"]))

    def end_element(self, name):
        if name == "move":
            move = self.move_stack.pop()
            self.tasks.append(move)
        self.current_element = None
        self.current_data = ""

    def char_data(self, data):
        self.current_data += data

    def clear_history(self):
        self.parser = xml.parsers.expat.ParserCreate()
        self.parser.Parse("<root>", False)  # give it a root element so that it won't end the document
        self.parser.StartElementHandler = self.start_element
        self.parser.EndElementHandler = self.end_element
        self.parser.CharacterDataHandler = self.char_data
        self.current_element = None
        self.current_data = ""
        self.move_stack = []
        self.current_move_start_time = None
        self.current_move_stop_time = None
