import anthropic

client = anthropic.Anthropic(api_key="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")

message = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=10,
    messages=[{"role": "user", "content": "Dis bonjour"}]
)

print(message.content[0].text)