from openai import OpenAI

client = OpenAI(api_key="sk-d5e17aa3fd6c48a1b9db13e83c379a9e", base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False
)

print(response.choices[0].message.content)
