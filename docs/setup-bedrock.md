# Using Amazon Bedrock (alternative)

The workshop runs on DeepSeek by default ([setup](setup-deepseek.md)). Use Bedrock only if the
instructor provides you a **personal Bedrock API key**. You do **not** need an AWS account,
the AWS CLI, or any AWS login.

1. Open your `.env` file and set:
   ```
   MODEL_PROVIDER=bedrock
   AWS_BEARER_TOKEN_BEDROCK=<the key you received>
   AWS_REGION=eu-west-1          # keep what the instructor tells you
   BEDROCK_MODEL=eu.anthropic.claude-sonnet-5-5  # keep what the instructor tells you
   ```
2. Test it:
   ```bash
   python scripts/check_setup.py
   ```

## Switching models
Change `BEDROCK_MODEL` to any model ID the instructor lists as enabled, then restart `adk web`.
IDs starting with `eu.` / `us.` are *cross-region inference profiles*. Use the prefix that matches your region.

## Troubleshooting
| Error contains | Meaning / fix |
|---|---|
| `AWS_BEARER_TOKEN_BEDROCK is not set` | The key is missing from `.env` or still has the `<...>` placeholder |
| `403` / `AccessDenied` / `not authorized` | Key expired or mistyped: ask the instructor |
| `ValidationException ... model identifier is invalid` | Wrong `BEDROCK_MODEL` ID or wrong region prefix |
| `ResourceNotFound` / `model access` | That model isn't enabled in the instructor's account: pick another |
| `ThrottlingException` | Too many requests at once: wait a few seconds and retry |

**Keep your key private.** Don't commit `.env`, and don't paste the key in chats or screenshots.
