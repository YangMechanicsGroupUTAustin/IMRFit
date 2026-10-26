# Contributing to IMRFit

Thank you for helping improve IMRFit. Bug reports, documentation fixes, tests,
and changes to the GUI or numerical models are welcome.

## Questions and bug reports

Use [GitHub Issues](https://github.com/YangMechanicsGroupUTAustin/IMRFit/issues)
for questions, installation problems, and bug reports. Before opening an issue,
check whether it has already been reported. For a bug, please include:

- Your operating system, Python version, and whether you used the source code or an executable release.
- The IMRFit version or commit, the model and workflow involved, and steps to reproduce the problem.
- The expected and observed behavior, plus an error message or screenshot if available.
- A minimal MAT file or parameter set when the problem depends on data. Remove private or identifying data before sharing it publicly.

For a larger feature or model change, open an issue first to discuss the intended
behavior and how it will be verified.

## Development and pull requests

Follow the installation instructions in [README.md](README.md), then run the
existing tests from the repository root:

```sh
python -m unittest discover -s tests -v
```

Set `QT_QPA_PLATFORM=offscreen` when running GUI-related tests without a display;
the CI workflow does this automatically. Add or update focused tests for behavior
changes, and describe any numerical validation or manual GUI checks in the pull
request. Keep changes scoped, document new user-facing behavior, and do not commit
personal experimental data, credentials, or virtual environments.

Maintainers review issues and pull requests as availability permits. GitHub Issues
is also the support channel; there is no guaranteed response time. Contributions
are released under the repository's [MIT license](LICENSE).
