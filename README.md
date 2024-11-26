# upgrade-dependencies

CLI tool to check for dependency updates in your python project. Automatically creates
GitHub pull requests for dependencies you wish to update!

## Limitations

- Currently only supports a single specifier.
- File structure is fixed
- GH actions must only use major version
- Recommend to have a clean git before running (or at least no changes to pyproject etc.)

## TODO

- [x] Async data retrieval
- [x] Get dependencies from github actions
- [x] Get uv dependency from github actions
- [x] Get dependencies from pre-commit
- [x] Github auth & async
- [x] Create dependency abstract class
- [x] Use get_dependency
- [x] Implement CLI
- [x] Create changes to files
- [ ] Handle uv better (not group)
- [x] Create pull request
- [ ] Documentation
- [ ] Add tests
