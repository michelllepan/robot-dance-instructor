import abc
import asyncio
import re
import xml.parsers.expat
import xml.parsers.expat
from typing import TypeVar


class RuntimeSession(abc.ABC):
    pass


RuntimeSessionObject = TypeVar('RuntimeSessionObject', bound=RuntimeSession)


class Runtime[RuntimeSessionObject](abc.ABC):
    @abc.abstractmethod
    async def start_session(self) -> RuntimeSessionObject:
        pass

    @abc.abstractmethod
    async def define_move(self, session: RuntimeSessionObject, move_id: str, start_time: float, stop_time: float):
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
            self.move_stack.append(attrs["id"])
            self.current_move_start_time = None
            self.current_move_stop_time = None
        elif name == "word":
            start_time = float(attrs["start"])
            stop_time = float(attrs["end"])
            if self.current_move_start_time is None or start_time < self.current_move_start_time:
                self.current_move_start_time = start_time
            if self.current_move_stop_time is None or stop_time > self.current_move_stop_time:
                self.current_move_stop_time = stop_time
        elif name == "response":
            if "command" in attrs:
                command = attrs["command"]
                move_commands = command.split(';')
                for move_command in move_commands:
                    if move_command.strip():
                        match = re.match(r'move\((\d+)\)', move_command.strip())
                        if match:
                            move_id = match.group(1)
                            self.tasks.append(self.runtime.do_move(self.execute_session, move_id))
            elif "speech" in attrs:
                self.tasks.append(self.runtime.speech(self.execute_session, attrs["speech"]))

    def end_element(self, name):
        if name == "move":
            move_id = self.move_stack.pop()
            self.tasks.append(self.runtime.define_move(
                self.execute_session,
                move_id,
                self.current_move_start_time,
                self.current_move_stop_time
            ))
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
