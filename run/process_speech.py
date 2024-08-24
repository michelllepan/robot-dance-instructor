import asyncio
import json
import os
import re
import time
import tkinter as tk
from tkinter import ttk

import azure.cognitiveservices.speech as speechsdk
import dotenv
import redis.asyncio as redis

from instructor.speech.engine import Runtime, RuntimeSession, Engine
from instructor.speech.prompt import Conversation

dotenv.load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

DEFINE_MOVE_KEY = "robot::define_move"
MOVE_LIST_KEY = "robot::move_list"
EXECUTE_FLAG_KEY = "teleop::replay_ready"
MOVE_EXECUTED_KEY = "robot::move_executed"


class AppSessionObject(RuntimeSession):
    def __init__(self):
        self.pending_moves = []
        self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)


class SpeechRecognizerApp(Runtime):
    def __init__(self, root):
        self.root = root
        self.root.title("Speech Recognizer")

        self.recording = False
        self.recognizer = None
        self.audio_stream = None

        self.history = []
        self.start_time = None
        self.current_duration = 0

        self.create_widgets()
        self.setup_speech_recognizer()
        self.setup_grid()

        self.conversation = Conversation(api_key=OPENAI_API_KEY)

        self.engine = Engine(runtime=self)

    # ---- UI ----

    def create_widgets(self):
        self.start_button = ttk.Button(self.root, text="Start Recording", command=self.toggle_recording)
        self.start_button.grid(row=0, column=0, padx=10, pady=10)

        self.duration_label = ttk.Label(self.root, text="Duration: 0.0 s")
        self.duration_label.grid(row=0, column=1, padx=10, pady=10, sticky="e")

        self.tree = ttk.Treeview(self.root, columns=("Recognized", "Processed", "Start Time", "Stop Time"),
                                 show="headings")
        self.tree.heading("Recognized", text="Recognized Sentence")
        self.tree.heading("Processed", text="Processed Sentence")
        self.tree.heading("Start Time", text="Start Time")
        self.tree.heading("Stop Time", text="Stop Time")
        self.tree.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        # Add console text box
        self.console = tk.Text(self.root, wrap=tk.WORD, height=5)
        self.console.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        # Add scrollbar for console
        self.console_scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.console.yview)
        self.console_scrollbar.grid(row=2, column=3, sticky="ns")
        self.console.configure(yscrollcommand=self.console_scrollbar.set)

    def setup_grid(self):
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)  # Make console resizable
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)

    def log_to_console(self, message):
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)

    # ---- Speech Recognition ----
    def setup_speech_recognizer(self):
        speech_key = AZURE_SPEECH_KEY
        service_region = AZURE_SPEECH_REGION

        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
        speech_config.request_word_level_timestamps()
        audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        self.recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        self.recognizer.recognizing.connect(self.recognizing_callback)
        self.recognizer.recognized.connect(self.recognized_callback)
        self.recognizer.session_stopped.connect(self.session_stopped_callback)

    def toggle_recording(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.recording = True
        self.start_button.config(text="Stop Recording")
        self.clear_history()
        self.start_time = time.time()
        self.recognizer.start_continuous_recognition()
        self.update_duration()

    def stop_recording(self):
        self.recording = False
        self.start_button.config(text="Start Recording")
        self.recognizer.stop_continuous_recognition()

    def clear_history(self):
        self.history.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

    def recognizing_callback(self, evt):
        text = evt.result.text
        self.update_history(text, stable=False)

    def recognized_callback(self, evt):
        result = json.loads(evt.result.json)
        best_result = result['NBest'][0]
        words = best_result['Words']

        # text = evt.result.text # Good for display but often not matching the word timings
        word_timings = [(word['Word'], word['Offset'] / 10_000_000, (word['Offset'] + word['Duration']) / 10_000_000)
                        for word in words]

        self.update_history(best_result['Lexical'], word_timings, stable=True)

    def session_stopped_callback(self, evt):
        print("Session stopped")

    def update_duration(self):
        if self.recording:
            self.current_duration = time.time() - self.start_time
            self.duration_label.config(text=f"Duration: {self.current_duration:.1f} s")
            self.root.after(100, self.update_duration)

    def update_history(self, text, word_timings=None, stable=False):
        if stable:
            asyncio.run(self.process_stable_sentence(text, word_timings))
        else:
            self.update_unstable_entry(text)

    async def process_stable_sentence(self, sentence, word_timings):
        start_time = word_timings[0][1]
        stop_time = word_timings[-1][2]
        start_time_str = f"{start_time:.1f} s"
        stop_time_str = f"{stop_time:.1f} s"

        # Find the last unstable entry
        unstable_items = [item for item in self.tree.get_children() if "unstable" in self.tree.item(item, "tags")]
        if unstable_items:
            item = unstable_items[-1]
            self.tree.delete(item)
        else:
            item = ""

        # Insert the stable entry at the top
        new_item = self.tree.insert("", "end", values=(sentence, "processing...", start_time_str, stop_time_str),
                                    tags=("stable",))
        self.tree.tag_configure("stable", foreground="black")

        processed_sentence = await self.process(sentence, word_timings)
        self.tree.item(new_item, values=(sentence, processed_sentence, start_time_str, stop_time_str))

        # Add a new unstable entry at the bottom for the next sentence
        self.tree.insert("", "end", values=("", "", "", ""), tags=("unstable",))
        self.tree.tag_configure("unstable", foreground="grey")

    def update_unstable_entry(self, sentence):
        unstable_items = [item for item in self.tree.get_children() if "unstable" in self.tree.item(item, "tags")]
        if unstable_items:
            last_item = unstable_items[-1]
            self.tree.item(last_item, values=(sentence, "", "", ""))
        else:
            self.tree.insert("", "end", values=(sentence, "", "", ""), tags=("unstable",))
        self.tree.tag_configure("unstable", foreground="grey")

    def update_last_entry(self, sentence):
        if self.tree.get_children():
            last_item = self.tree.get_children()[-1]
            self.tree.item(last_item, values=(sentence, "", "", ""))
        else:
            self.tree.insert("", "end", values=(sentence, "", "", ""), tags=("unstable",))
        self.tree.tag_configure("unstable", foreground="grey")

    # ---- Parsing ----
    async def process(self, sentence, word_timings):
        parsed_sentence = await self.conversation.get_gpt_parsed(sentence)
        processed_sentence = self.add_timings_to_parsed_sentence(sentence, parsed_sentence, word_timings)
        await self.engine.execute(processed_sentence)
        print(processed_sentence)
        return parsed_sentence

    def add_timings_to_parsed_sentence(self, original_sentence, parsed_sentence, word_timings):
        original_words = original_sentence.split()
        word_index = 0
        result = []
        current_text = ""

        # Function to process accumulated text
        def process_text(text):
            nonlocal word_index
            words = text.split()
            processed_words = []
            for word in words:
                if word_index < len(word_timings):
                    original_word, start_time, end_time = word_timings[word_index]
                    if re.sub(r'[^\w\s]', '', word.lower()) == re.sub(r'[^\w\s]', '', original_word.lower()):
                        processed_words.append(f'<word start="{start_time:.3f}" end="{end_time:.3f}">{word}</word>')
                        word_index += 1
                    else:
                        processed_words.append(word)
                else:
                    processed_words.append(word)
            return ' '.join(processed_words)

        # Iterate through the parsed sentence
        i = 0
        while i < len(parsed_sentence):
            if parsed_sentence[i] == '<':
                # Process any accumulated text before the tag
                if current_text:
                    result.append(process_text(current_text))
                    current_text = ""

                # Find the end of the tag
                tag_end = parsed_sentence.find('>', i)
                if tag_end != -1:
                    tag = parsed_sentence[i:tag_end + 1]
                    result.append(tag)
                    i = tag_end + 1
                else:
                    # If no closing '>' is found, append the rest of the string and break
                    result.append(parsed_sentence[i:])
                    break
            else:
                current_text += parsed_sentence[i]
                i += 1

        # Process any remaining text
        if current_text:
            result.append(process_text(current_text))

        return ''.join(result)

    # ---- Runtime ----
    async def start_session(self) -> AppSessionObject:
        self.log_to_console("Starting session")
        session = AppSessionObject()
        await session.redis.delete(MOVE_LIST_KEY)
        await session.redis.set(EXECUTE_FLAG_KEY, "0")
        return session

    async def define_move(self, session: AppSessionObject, move_id: str, start_time: float, stop_time: float):
        self.log_to_console(f"Defining move {move_id} from {start_time:.1f} s to {stop_time:.1f} s")
        move_data = f"{move_id}:{start_time + self.start_time:.3f}:{stop_time + self.start_time:.3f}"
        await session.redis.rpush(DEFINE_MOVE_KEY, move_data)

    async def do_move(self, session: AppSessionObject, move_id: str):
        self.log_to_console(f"Queueing move {move_id}")
        session.pending_moves.append(move_id)

    async def speech(self, session: AppSessionObject, speech: str):
        self.log_to_console(f"Executing speech: {speech}")
        # Implement text-to-speech functionality here if needed

    async def end_session(self, session: AppSessionObject):
        self.log_to_console("Ending session")
        self.log_to_console(f"Executing moves: {session.pending_moves}")

        # Add pending moves to the Redis list
        if len(session.pending_moves) > 0:
            for move_id in session.pending_moves:
                await session.redis.rpush(MOVE_LIST_KEY, move_id)

            # Set the execute flag to trigger the robot controller
            await session.redis.set(EXECUTE_FLAG_KEY, "1")

            # Wait for the robot to execute all moves
            while True:
                executed_moves = await session.redis.llen(MOVE_EXECUTED_KEY)
                if executed_moves == len(session.pending_moves):
                    break
                await asyncio.sleep(0.1)


        self.log_to_console("All moves executed")

        # Clear the executed moves list
        await session.redis.delete(MOVE_EXECUTED_KEY)


if __name__ == "__main__":
    root = tk.Tk()
    app = SpeechRecognizerApp(root)
    root.mainloop()
