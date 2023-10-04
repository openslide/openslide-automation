This repository contains infrastructure for automatically building and
testing OpenSlide.

- `autobuild`: automatic nightly build from Git main
- `buildbot`: fragments of obsolete Buildbot configuration


## About openslide-bot

There are two shortcomings of using [`GITHUB_TOKEN`][GITHUB_TOKEN] in an
Actions workflow to create issues or PRs, comment on issues, etc.
One is that it requires giving too many privileges to the workflow, e.g.
if a workflow needs to create a new issue, it must be given write access to
all issues in the repo.
The other is that events caused by `GITHUB_TOKEN` do not initiate workflows,
so a PR created with the token won't automatically run CI.

To address both problems, all OpenSlide repos have access to a GitHub
Actions secret with a Personal Access Token for the
[**@openslide-bot**][openslide-bot] account.
The bot account is a member of the OpenSlide organization, solely so its
profile page shows the affiliation, but doesn't have any special permissions
to OpenSlide repos.
Workflows can thus opt to interact with OpenSlide repos as a normal user.

Since [**@openslide-bot**][openslide-bot] doesn't have permission to push
branches directly to OpenSlide repos, it has its own forks for storing PR
branches.
Those forks typically have a stale `main` branch, so PR branches will often
incidentally include workflow files newer than the ones in `main`.
As a result, the bot's PAT needs [`workflow` scope][workflow scope] so the
PR branches won't be rejected on push.
To avoid thus allowing arbitrary code execution as the bot user, the bot's
forks must all have GitHub Actions disabled.

[GITHUB_TOKEN]: https://docs.github.com/en/actions/security-guides/automatic-token-authentication
[openslide-bot]: https://github.com/openslide-bot
[workflow scope]: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes
