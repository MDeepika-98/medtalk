

from openai import OpenAI

def chat_with_nvidia_model(user_prompt: str, api_key: str):
    """Chat with NVIDIA's hosted model using OpenAI-compatible SDK."""
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="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"
    )

    # Prepare the chat messages
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": user_prompt}
    ]

    # Request streamed response from the model
    completion = client.chat.completions.create(
        model="deepseek-ai/deepseek-r1-distill-llama-8b",
        messages=messages,
        temperature=0.6,
        top_p=0.7,
        max_tokens=512,
        stream=True
    )

    # Print streamed content
    for chunk in completion:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="")

