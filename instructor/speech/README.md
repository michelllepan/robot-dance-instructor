Robot Instructor
================
Jackie (Junrui) Yang
--------------------

Use speech to tell your robot to do different moves.

## Features

- Real-time speech recognition
- Natural language processing to interpret commands
- GUI for visualizing recognized speech and processed commands
- Redis-based communication for robot move definition and execution
- Simulated robot move definition and execution

## Prerequisites

- Python 3.11 (tested on)
- Azure Speech Services account
- OpenAI API key
- Redis server

## Installation

1. Clone the repository:
   ```
   git clone git@github.com:StanfordHCI/RobotInstructor.git
   cd RobotInstructor
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root and add your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   AZURE_SPEECH_KEY=your_azure_speech_key
   AZURE_SPEECH_REGION=your_azure_speech_region
   ```

4. Ensure you have a Redis server running. By default, the application will try to connect to Redis on localhost:6379. If your Redis server is on a different host or port, update the `REDIS_HOST` and `REDIS_PORT` constants in `main.py`.

## Usage

1. Start your Redis server if it's not already running.

2. Run the main application:
   ```
   python main.py
   ```

3. Click "Start Recording" to begin speech recognition.
4. Speak commands to define moves or ask the robot to perform actions.
5. The GUI will display recognized speech and processed commands.
6. The application will communicate with the robot controller through Redis.
7. Click "Stop Recording" to end the session.

## Redis Communication

The application uses Redis for communication with the robot controller:

- `robot::move_list`: A list of moves to be executed by the robot.
- `robot::execute_flag`: A flag to signal the robot controller to start executing moves.
- `robot::move_executed`: A list of moves that have been executed by the robot.

The robot controller should monitor these Redis keys and update them accordingly.

## Example Conversation

User: "Hi robot, let's create some dance moves."

Robot: "Hello! I'd be happy to help you create some dance moves. What would you like to start with?"

User: "Let's start with move number 1. Watch me."
(User demonstrates a dance move)

Robot: "Alright, I've recorded that as move number 1. What would you like to do next?"

User: "Now, let's create move number 2. It goes like this."
(User demonstrates another dance move)

Robot: "Great! I've recorded that as move number 2. Is there anything else you'd like to do?"

User: "Can you perform move 1 twice and then move 2 once?"

Robot: "Certainly! I'll perform move 1 twice and then move 2 once for you."
(Robot performs the requested sequence of moves)

## Project Structure

- `main.py`: The main application file containing the GUI, speech recognition logic, and Redis communication.
- `engine.py`: Defines the core engine for processing and executing commands.
- `prompt.py`: Handles communication with the GPT model for natural language processing.
- `requirements.txt`: Lists all required Python packages.

## Note

This project assumes a separate robot controller that will read from and write to the specified Redis keys. The robot controller implementation is not included in this repository.