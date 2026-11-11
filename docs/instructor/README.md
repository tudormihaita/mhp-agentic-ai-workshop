# Instructor notes

## Before the workshop
1. **Bedrock models:** in the AWS console (Bedrock → Model catalog), make sure the models listed in
   `.env.example` are available in your region, and test one with your own key.
   Update `AWS_REGION` / `BEDROCK_MODEL` in `.env.example` if you use other models.
2. **Student keys:** `python docs/instructor/bedrock_keys.py create --count 12 --days 7`
   → `students.keys.csv` (git-ignored). Hand out one key per student privately.
3. **Budget alarm:** AWS Billing → Budgets → a small monthly budget with an email alert.
4. Ask students to complete the README setup and run `python scripts/check_setup.py` **before** the
   session. Ollama users must also pull their model in advance.

## After the workshop
`python docs/instructor/bedrock_keys.py delete`. Removes all `workshop-student-*` users and their keys.

## Notes
- Long-term Bedrock API keys are intended for exploration, not production. Short expiry + delete afterwards.
- `bedrock_keys.py` reads the key from `ServiceApiKeyValue` or `ServiceCredentialSecret`, since the field
  name differs between boto3 versions. Check the first generated key with `check_setup.py`.
