# `upgrade-dependencies`

**Usage**:

```console
$ upgrade-dependencies [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `list-dependencies`: List all the dependencies for the project.
* `check-dependency`: Checks whether a dependency needs updating.
* `needs-updating`: Lists the dependencies that need updating.
* `latest-versions`: List the dependencies that aren't specified to the latest version.
* `update`: Updates a dependency to a specific (or latest) version.
* `format-yml`: Formats the workflow and pre-commit config yaml files.

## `upgrade-dependencies list-dependencies`

List all the dependencies for the project.

**Usage**:

```console
$ upgrade-dependencies list-dependencies [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `upgrade-dependencies check-dependency`

Checks whether a dependency needs updating.

**Usage**:

```console
$ upgrade-dependencies check-dependency [OPTIONS] DEPENDENCY
```

**Arguments**:

* `DEPENDENCY`: Name of the dependency to check  [required]

**Options**:

* `--help`: Show this message and exit.

## `upgrade-dependencies needs-updating`

Lists the dependencies that need updating.

**Usage**:

```console
$ upgrade-dependencies needs-updating [OPTIONS]
```

**Options**:

* `--base / --no-base`: Include base dependencies  [default: base]
* `--optional-deps / --no-optional-deps`: Include optional dependencies  [default: optional-deps]
* `--group-deps / --no-group-deps`: Include dependency groups  [default: group-deps]
* `--github-actions / --no-github-actions`: Include GitHub actions dependencies  [default: github-actions]
* `--pre-commit / --no-pre-commit`: Include pre-commit dependencies  [default: pre-commit]
* `--help`: Show this message and exit.

## `upgrade-dependencies latest-versions`

List the dependencies that aren't specified to the latest version.

**Usage**:

```console
$ upgrade-dependencies latest-versions [OPTIONS]
```

**Options**:

* `--base / --no-base`: Include base dependencies  [default: base]
* `--optional-deps / --no-optional-deps`: Include optional dependencies  [default: optional-deps]
* `--group-deps / --no-group-deps`: Include dependency groups  [default: group-deps]
* `--github-actions / --no-github-actions`: Include GitHub actions dependencies  [default: no-github-actions]
* `--pre-commit / --no-pre-commit`: Include pre-commit dependencies  [default: pre-commit]
* `--help`: Show this message and exit.

## `upgrade-dependencies update`

Updates a dependency to a specific (or latest) version.

Makes changes to the dependency specification locally and creates a GitHub pull
request on a new branch (branch name = dependency/{package_name}-{version}). Make
sure this branch name does not exist locally or on GitHub.

Requires git and the GitHub CLI to be installed. It is recommended to have a clean
git before running this command.

**Usage**:

```console
$ upgrade-dependencies update [OPTIONS] DEPENDENCY
```

**Arguments**:

* `DEPENDENCY`: Dependency to update  [required]

**Options**:

* `--version TEXT`: Version to update to, latest version if not specified
* `--target-branch TEXT`: Name of the branch to merge PR to  [default: master]
* `--help`: Show this message and exit.

## `upgrade-dependencies format-yml`

Formats the workflow and pre-commit config yaml files.

**Usage**:

```console
$ upgrade-dependencies format-yml [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.
