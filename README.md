# GoodWise

Integrates GoodLinks and Readwise. Sends your higlights to Readwise to be included in your Daily Review rotation.

## Setup

1. Get a Readwise [API key](https://readwise.io/access_token)
2. Save the key in a `.env` file:
```
READWISE_API_TOKEN=<your key>
```
3. Verify using `python3 sync_highlights.py --dry-run`
4. Run (via cron) `python3 sync_highlights.py`
