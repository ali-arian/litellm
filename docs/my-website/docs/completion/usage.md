# Usage 

LiteLLM returns the OpenAI compatible usage object across all providers.

```bash
"usage": {
    "prompt_tokens": int,
    "completion_tokens": int,
    "total_tokens": int
  }
```

## Quick Start 

```python
from litellm import completion
import os

## set ENV variables
os.environ["OPENAI_API_KEY"] = "your-api-key"

response = completion(
  model="gpt-3.5-turbo",
  messages=[{ "content": "Hello, how are you?","role": "user"}]
)

print(response.usage)
```

## Streaming Usage

if `stream_options={"include_usage": True}` is set, an additional chunk will be streamed before the data: [DONE] message. The usage field on this chunk shows the token usage statistics for the entire request, and the choices field will always be an empty array. All other chunks will also include a usage field, but with a null value.


```python
from litellm import completion 

completion = completion(
  model="gpt-4o",
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  stream=True,
  stream_options={"include_usage": True}
)

for chunk in completion:
  print(chunk.choices[0].delta)

```

## Prompt Caching 

For Anthropic + Deepseek, LiteLLM follows the Anthropic prompt caching usage object format:

```bash
"usage": {
    "prompt_tokens": int,
    "completion_tokens": int,
    "total_tokens": int, 
    "_cache_creation_input_tokens": int, # hidden param for prompt caching. Might change, once openai introduces their equivalent.
    "_cache_read_input_tokens": int # hidden param for prompt caching. Might change, once openai introduces their equivalent.
}
```

- `prompt_tokens`: These are the non-cached prompt tokens (same as Anthropic, equivalent to Deepseek `prompt_cache_miss_tokens`).
- `completion_tokens`: These are the output tokens generated by the model.
- `total_tokens`: Sum of prompt_tokens + completion_tokens.
- `_cache_creation_input_tokens`: Input tokens that were written to cache. (Anthropic only).
- `_cache_read_input_tokens`: Input tokens that were read from cache for that call. (equivalent to Deepseek `prompt_cache_hit_tokens`). 


### Anthropic Example 

```python 
from litellm import completion 
import litellm 
import os 

litellm.set_verbose = True # 👈 SEE RAW REQUEST
os.environ["ANTHROPIC_API_KEY"] = "" 

response = completion(
    model="anthropic/claude-3-5-sonnet-20240620",
    messages=[
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "You are an AI assistant tasked with analyzing legal documents.",
                },
                {
                    "type": "text",
                    "text": "Here is the full text of a complex legal agreement" * 400,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
        },
        {
            "role": "user",
            "content": "what are the key terms and conditions in this agreement?",
        },
    ]
)

print(response.usage)
```

### Deepeek Example 

```python 
from litellm import completion 
import litellm
import os 

os.environ["DEEPSEEK_API_KEY"] = "" 

litellm.set_verbose = True # 👈 SEE RAW REQUEST

model_name = "deepseek/deepseek-chat"
messages_1 = [
    {
        "role": "system",
        "content": "You are a history expert. The user will provide a series of questions, and your answers should be concise and start with `Answer:`",
    },
    {
        "role": "user",
        "content": "In what year did Qin Shi Huang unify the six states?",
    },
    {"role": "assistant", "content": "Answer: 221 BC"},
    {"role": "user", "content": "Who was the founder of the Han Dynasty?"},
    {"role": "assistant", "content": "Answer: Liu Bang"},
    {"role": "user", "content": "Who was the last emperor of the Tang Dynasty?"},
    {"role": "assistant", "content": "Answer: Li Zhu"},
    {
        "role": "user",
        "content": "Who was the founding emperor of the Ming Dynasty?",
    },
    {"role": "assistant", "content": "Answer: Zhu Yuanzhang"},
    {
        "role": "user",
        "content": "Who was the founding emperor of the Qing Dynasty?",
    },
]

message_2 = [
    {
        "role": "system",
        "content": "You are a history expert. The user will provide a series of questions, and your answers should be concise and start with `Answer:`",
    },
    {
        "role": "user",
        "content": "In what year did Qin Shi Huang unify the six states?",
    },
    {"role": "assistant", "content": "Answer: 221 BC"},
    {"role": "user", "content": "Who was the founder of the Han Dynasty?"},
    {"role": "assistant", "content": "Answer: Liu Bang"},
    {"role": "user", "content": "Who was the last emperor of the Tang Dynasty?"},
    {"role": "assistant", "content": "Answer: Li Zhu"},
    {
        "role": "user",
        "content": "Who was the founding emperor of the Ming Dynasty?",
    },
    {"role": "assistant", "content": "Answer: Zhu Yuanzhang"},
    {"role": "user", "content": "When did the Shang Dynasty fall?"},
]

response_1 = litellm.completion(model=model_name, messages=messages_1)
response_2 = litellm.completion(model=model_name, messages=message_2)

# Add any assertions here to check the response
print(response_2.usage)
```