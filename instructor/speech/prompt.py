import re
from typing import Optional

from instructor.moves.moves import Move
import openai

robot_prompt = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": "You are helping me tag the user's speech commands to a dancing robot.\n<conversation> and </conversation> will be given to you to mark the start and the end of the user's conversation. Different conversation have different context, don't carry over the context.\nYou need to provide <move type=\"{type}\"> to specify if the move is a replay, follow, take, point, or free-space.\nFor replay moves, you need to provide <move id=\"{id}\"> and </move> to mark the start and the end of the user's request to record a move, and an optional move edits array.\nSometimes, users may request you to perform a replay move, you can achieve that by using <response command=\"{command}\"/> command can be something like `move('replay',1,[]);move('replay',2,[]);`.\n You can edit replay moves to go slower, faster, or rotate-left and rotate-right with move('replay',2,['faster','rotate_right']) for example.\nFor follow moves, a user may ask you to follow them. Users can specify to follow a either right-hand or left-hand for an amount of seconds, and you can achieve that by using a <response command=\"{command}\"/> like 'move('follow')' or specified with `move('follow','right-hand',30);move('follow','left-hand',10);'.\nFor take moves, the user must specify an object to be taken or grabbed like 'move('take','apple').\nFor point moves, the user can point with either right or left hand and can optionally specify how far to move in that direction, with move('point') and move('point','right-hand',5) to move 5 feet in the direction the right hand is pointing.\nFor free-space moves, the user can specify to move in forward, backward, left or right for optionally any distance as well with 'move('free-space','forward',8);move('free-space','left')'.\nYou can also respond to user's request by <response speech=\"{response}\"/>.\nMake sure to include user's original speech in the tagging response."
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "<conversation>\nHi."
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "<conversation>\nHi. <response speech=\"Hello! How can I assist you with the dancing robot today?\"/>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Watch me do this move 1."
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "<move id=\"1\">Watch me do this move 1.</move>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Now this is move 2."
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "<move id=\"2\">Now this is move 2.</move>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Please do three move 1 and three move 2."
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Please do three move 1 and three move 2. <response command=\"move('replay',1,[]);move('replay',1,[]);move('replay',1,[]);move('replay',2,[]);move('replay',2,[]);move('replay',2,[]);\"/>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Please do move 1 slower and rotate left."
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Please do move 1 slower and rotate left. <response command=\"move('replay',1,['slower','rotate_left']);\"/>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Now perform move 2 faster and rotate right."
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Now perform move 2 faster and rotate right. <response command=\"move('replay',2,['faster','rotate_right']);\"/>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Go where I'm pointing. Then move 3 feet to the left."
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Go where I'm pointing. Then move 3 feet to the left. <response command=\"move('point');move('free-space','left',5);\"/>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "I'm pointing with my left hand. Can you go there then move backwards 3 feet?"
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "I'm pointing with my left hand. Can you go there then move backwards 3 feet? <response command=\"move('point','left-hand');move('free-space','back',3);\"/>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Nice. Thanks.\n</conversation>"
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Nice. Thanks. <response speech=\"You're welcome! If you need any more help, just let me know!\"/>\n</conversation>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Can you catch this? Or can you throw an object?\n</conversation>"
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Can you catch this? Or can you throw an object? <response speech=\"Sorry! You can teach me moves, ask me to follow your hands, go where you're pointing, take objects or move around the room! Let me know how I can help.\"/>\n</conversation>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "<conversation>\nCan you do move 1?"
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "<conversation>\nCan you do move 1? <response speech=\"Sorry. I'm not sure how to do move 1 yet. Can you teach me how to do move 1.\"/>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Here is move 1."
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "<move id=\"1\">Here is move 1.</move>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Now do move 2 and 1."
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Now do move 2 and 1. <response speech=\"Sorry. I'm not sure how to do move 2.\"/>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "What can you do? \n</conversation>"
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "What can you do? <response speech=\"You can teach me moves, instruct me to move around the room or where you point, take objects, and follow your hands! Let me know what you'd like me to do.\"/>\n</conversation>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Follow my right hand for 10 seconds."
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Follow my right hand for 10 seconds. <response command=\"move('follow','right-hand',10);\"/>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Go where my left hand is pointing then move backwards 3 feet and move forwards."
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Go where my left hand is pointing then move backwards 3 feet and move forwards. <response command=\"move('point','left-hand');move('free-space','backwards',3);move('free-space','forward')\"/>"
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "</conversation>"
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "</conversation>"
            }
        ]
    }
]

class Conversation:
    def __init__(self, api_key: str):
        self.messages = []
        self.openai = openai.AzureOpenAI(
          azure_endpoint="https://reactgenie-openai.openai.azure.com/", 
          api_key=api_key,
          api_version="2024-02-01",
        )

    async def get_gpt_parsed(self, text: str) -> Optional[str]:
        if len(self.messages) == 0:
            text = "<conversation>\n" + text
        self.messages.append({
          "content": text,
          "role": "user",
        })
        response = self.openai.chat.completions.create(
            model="reactgenie",
            messages=robot_prompt + self.messages,
            max_tokens=500,
            temperature=0.0
        )
        self.messages.append(response.choices[0].message)
        return response.choices[0].message.content
    
def parse_command(self, command: str) -> Move:
    """
    Parses a command string to create a corresponding Move object with defaults that can be overwritten.
    """
    # Regex to match the structure of the move command
    move_match = re.match(r"move\('(.*?)',(.*?)(?:,(.*?))?\)", command.strip())
    if not move_match:
        raise ValueError(f"Invalid move command: {command}")

    move_type = move_match.group(1)
    primary_param = move_match.group(2).strip().strip("'")  # strip any quotes
    extra_params = move_match.group(3)  # any additional parameters (e.g., list of modifiers)

    # Create and return the correct Move object based on move type
    if move_type == 'replay':
        replay_id = primary_param
        edits = eval(extra_params) if extra_params else []  # Convert string to list
        return Move(
            move_type='replay',
            replay_id=replay_id,
            move_edits=edits
        )

    elif move_type == 'follow':
        # `primary_param` is hand ('right-hand' or 'left-hand'), and `extra_params` is the duration
        hand = primary_param if primary_param in ['right-hand', 'left-hand'] else 'right-hand'  # Default to 'right-hand'
        duration = float(extra_params) if extra_params else 10.0  # Default to 10 seconds
        return Move(
            move_type='follow',
            hand=hand,
            duration=duration
        )

    elif move_type == 'take':
        # `primary_param` is the object to take
        object_to_take = primary_param
        return Move(
            move_type='take',
            object_to_take=object_to_take
        )

    elif move_type == 'free-space':
        # `primary_param` is magnitude, `extra_params` is direction
        magnitude = float(primary_param) if primary_param else 5.0  # Default to magnitude 5
        direction = extra_params.strip().strip("'") if extra_params else 'forwards'  # Default to 'forwards'
        return Move(
            move_type='free-space',
            magnitude=magnitude,
            direction=direction
        )

    elif move_type == 'point':
        # `primary_param` is magnitude, `extra_params` could be hand
        magnitude = float(primary_param) if primary_param else 5.0  # Default to magnitude 5

        # Check if hand is provided in extra_params, default to 'right-hand' otherwise
        hand = 'right-hand'  # Default hand
        if extra_params:
            extra_params_clean = extra_params.strip().strip("'")
            if extra_params_clean in ['right-hand', 'left-hand']:
                hand = extra_params_clean
        
        return Move(
            move_type='point',
            magnitude=magnitude,
            hand=hand
        )

    else:
        raise ValueError(f"Unsupported move type: {move_type}")

