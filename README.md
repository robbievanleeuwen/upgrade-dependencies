# upgrade-dependencies

CLI tool to check for dependency updates in your python project. Automatically creates
GitHub pull requests for dependencies you wish to update!

## Usage

If you have `uv` installed, you can install `upgrade-dependencies` with

```
uv tool install upgrade-dependencies
```

You can then navigate to your project directory and execute:

```
uvx upgrade-dependencies [OPTIONS] COMMAND [ARGS]...
```

See the [CLI documentation](docs/usage.md) for information about how each command works.

### Requirements

All python requirements are installed by default. To successfully use the `update`
command the following executables must be installed into your shell:

- `git`
- `gh`, i.e. GitHub CLI - ensure you have already run `gh auth login` and added
  appropriate permissions

### GitHub API Rate Limit

The GitHub API is used to fetch data for GitHub actions and `pre-commit` repos.
Unauthenticated users have a rate limit of 60 requests per hour, whereas authenticated
users have a rate limit of 5,000 requests per hour. You can use a GitHub personal access
token to utilise this higher rate limit by setting the `GH_PAT` environment variable:

```
export GH_PAT=github_pat_xxx
```

## Limitations

- Currently only supports a single specifier, e.g. `numpy~=2.0.2`, not `numpy>=2,<2.1`
- The project file structure is fixed and assumed, see
  [Project File Structure](#project-file-structure).
- GH actions must only use major version, e.g. `actions/checkout@v4` not
  `actions/checkout@v4.2.2`
- It is recommended to have a clean git before running `update` (a warning will be
  printed to the terminal if this is not the case).

## Project File Structure

The following project file structure is assumed:

```
project
├── .github
│   └── workflows
│       └── *.yml
├── .pre-commit-config.yml
└── pyproject.toml
```
