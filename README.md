# upgrade-dependencies

Creates PRs for dependency updates in python projects.

## Limitations

- Currently only supports a single specifier.
- File structure is fixed
- GH actions must only use major version

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
- [ ] Add tests
- [ ] Documentation
