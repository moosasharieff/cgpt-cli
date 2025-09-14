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

Store your API key (and optional base URL):

```bash
cgpt login
cgpt where   # show config path
```

Example:

```text
$ cgpt login
Enter API key: ********
Repeat for confirmation: ********
Do you want to set a custom base URL? [y/N]: n
✅ Saved credentials to: /home/you/.config/cgpt/config.toml
```

Config is stored at:

* Linux/macOS: `~/.config/cgpt/config.toml`
* Windows: `%APPDATA%\cgpt\config.toml`

If no config is found, `OPENAI_API_KEY` env var is used.



## Development

```bash
pytest -q          # run tests
make sanity-check  # build + verify CLI
```



## License

MIT © Mohammed Moosa Sharieff
