# ChatGPT CLI

![PyPI version](https://img.shields.io/pypi/v/cgpt-cli.svg)

Tiny ChatGPT terminal client.

- PyPI: https://pypi.org/project/cgpt-cli/
- License: MIT



## Quickstart

```bash
make venv
source .venv/bin/activate        # macOS/Linux
# .\.venv\Scripts\Activate.ps1    # Windows

make compile
make install-dev
````



## Authentication

Get an OpenAI API key from:
👉 [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys)

Store it via CLI:

```bash
cgpt login
cgpt where   # show config path
```

Config path:

* Linux/macOS: `~/.config/cgpt/config.toml`
* Windows: `%APPDATA%\cgpt\config.toml`

If no config is found, `OPENAI_API_KEY` env var is used:

```bash
export OPENAI_API_KEY="your-key"   # macOS/Linux
setx OPENAI_API_KEY "your-key"     # Windows PowerShell
```



## Configure Defaults

Use `cgpt set` to configure defaults like model and mode:

```bash
# Set a default model
cgpt set --model gpt-4o

# Set default mode (responses | chat)
cgpt set --mode responses

# Set both model and mode at once
cgpt set --model gpt-4o-mini --mode chat
```

Example config file:

```toml
api_key       = "sk-...redacted..."
default_model = "gpt-4o-mini"
default_mode  = "chat"
```



## Development

```bash
pytest -q          # run tests
make sanity-check  # build + verify CLI
```



## License

MIT © Mohammed Moosa Sharieff
