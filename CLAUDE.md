# Notes for Claude sessions

Shared tooling for the owner's Zepp OS projects (raetha/zepp-kestrel, raetha/zepp-watch-faces, more later): GitHub Actions and scripts for building, test builds, Zepp previews, releases and the emulator. Read `README.md` and `docs/plan.md` first.

- **Branches:** work on `dev`; never push to `main`. A release is one squash-merged pull request from `dev` into `main`, opened when the owner asks: it sets `pyproject.toml`'s and `zepp_devkit/__init__.py`'s version and dates the changelog section. After the merge, CI tags `main` as `vX.Y.Z`, publishes the GitHub release and resets `dev` to `main` (`release.yml`). Projects pin a commit with the version in a comment, and Dependabot proposes updates there.
- **Repository settings:** a ruleset protects `main` (pull requests, squash only); merged branches are deleted automatically; a classic rule keeps `dev` from being deleted and allows force pushes: after a release squash merge, CI resets `dev` onto `main` (`sync-dev` in `release.yml`) when nothing new landed on `dev` meanwhile; otherwise reset it by hand once that work is released (`git checkout dev && git reset --hard origin/main && git push --force-with-lease`).
- Record each change under `## [Unreleased]` in `CHANGELOG.md`, written for the projects using it. Never bump a version or date the changelog without being asked.
- **Behaviour changes reach every project.** Keep inputs backwards compatible within a major version; a breaking change is a new major version, with the migration in the changelog. Test with the fake Zeus (`test/`), and then in a project's CI before releasing.
- **Security:** the Zepp login is in each project's secrets, never here. Never print it, the Zepp app's log, or `zeus bridge` output. Actions pinned to commits; `contents: read` unless a job needs more.
- Project-specific things (page layouts and wording, app IDs, which watches, the HA component) stay in each project, passed in as inputs.
- Licence: MIT.
