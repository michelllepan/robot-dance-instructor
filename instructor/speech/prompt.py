from typing import Optional

import openai

robot_prompt = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": "You are helping me tag the user's speech commands to a dancing robot.\n<conversation> and </conversation> will be given to you to mark the start and the end of the user's conversation. Different conversation have different context, don't carry over the context.\nYou need to provide <move id=\"{id}\"> and </move> to mark the start and the end of the user's request to record a move.\nSometimes, users may request you to perform a certain move, you can achieve that by using <response command=\"{command}\"/> command can be something like `move(1);move(2);`.\nYou can also respond to user's request by <response speech=\"{response}\"/>.\nMake sure to include user's original speech in the tagging response."
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
                "text": "Please do three move 1 and three move 2. <response command=\"move(1);move(1);move(1);move(2);move(2);move(2);\"/>"
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
                "text": "<conversation>\nCan you do move 1?"
            }
        ]
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "<conversation>\nCan you do move 1? <response speech=\"Sorry. I'm not sure how to do move 1.\"/>"
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
