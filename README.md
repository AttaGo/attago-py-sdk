# attago — Python SDK

[![CI](https://github.com/AttaGo/attago-py-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/AttaGo/attago-py-sdk/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/attago)](https://pypi.org/project/attago/)
Python SDK for the [AttaGo](https://attago.bid) crypto trading dashboard API.

## Install

```bash
pip install attago
```

## Quick Start

### API Key Authentication

```python
import asyncio
from attago import AttaGoClient

async def main():
    async with AttaGoClient(api_key="ak_live_abc123") as client:
        score = await client.agent.get_score("BTC")
        print(f"{score.token}: {score.composite.signal} ({score.composite.score:.1f})")

asyncio.run(main())
```

### Sync Mode

```python
from attago import AttaGoClient

client = AttaGoClient(api_key="ak_live_abc123", sync=True)
score = client.agent.get_score_sync("BTC")
print(score.composite.signal)
client.close()
```

### x402 Signer Authentication

```python
from attago import AttaGoClient

client = AttaGoClient(signer=my_wallet_signer)
score = await client.agent.get_score("BTC")
```

### Cognito Authentication

```python
from attago import AttaGoClient

client = AttaGoClient(
    email="user@example.com",
    password="...",
    cognito_client_id="abc123",
)
await client.auth.sign_in()
profile = await client.data.get_latest()
```

## API Reference

| Service | Methods |
|---------|---------|
| `client.agent` | `get_score(symbol)`, `get_data(*symbols)` |
| `client.data` | `get_latest()`, `get_token_data(token)`, `get_data_push(request_id)` |
| `client.subscriptions` | `catalog()`, `list()`, `create(input)`, `update(sub_id, input)`, `delete(sub_id)` |
| `client.payments` | `subscribe(input)`, `status()`, `upgrade_quote(tier, cycle)` |
| `client.wallets` | `register(input)`, `list()`, `remove(address)` |
| `client.webhooks` | `create(url)`, `list()`, `delete(id)`, `send_test(opts)`, `send_server_test(id)` |
| `client.mcp` | `initialize()`, `list_tools()`, `call_tool(name, args)`, `ping()` |
| `client.api_keys` | `create(name)`, `list()`, `revoke(key_id)` |
| `client.bundles` | `list()`, `purchase(input)` |
| `client.push` | `list()`, `create(input)`, `delete(sub_id)` |
| `client.redeem` | `redeem(code)` |

## Webhook Listener

```python
from attago import WebhookListener

listener = WebhookListener(secret="whsec_...", port=4000)
listener.on_alert(lambda p: print(f"{p.alert.token}: {p.alert.state}"))
listener.on_test(lambda p: print("Test received"))
listener.start()
```

## Signature Verification

```python
from attago import verify_signature

body = request.body  # raw bytes
signature = request.headers["X-AttaGo-Signature"]
if verify_signature(body, webhook_secret, signature):
    # valid
```

## Error Handling

```python
from attago import AttaGoClient, ApiError, PaymentRequiredError, RateLimitError

try:
    score = await client.agent.get_score("BTC")
except PaymentRequiredError as e:
    print(f"Payment needed: {e.payment_requirements}")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except ApiError as e:
    print(f"API error {e.status_code}: {e.message}")
```
