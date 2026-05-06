# RepoUpdater

This repo contains a script that lets you apply changes to all OpenSAFELY
research repos at once, and then create a pull request for each repo.

## Status

This script has no tests, use with caution!

## Setup

Create virtual environment, .env file and install requirements.
```
just devenv
```

* Create a GitHub personal access token with all repo permissions, and update
  it the `ORG_TOKEN` variable in the `.env` file.

* If required, create a `config.yaml` file in the following format, listing repos to ignpre:

```
---
non_study_repos:
  - opensafely/documentation
  - opensafely/dummy-data-workshop
  - opensafely/ehrql-tutorial
```

## Usage example

```
# List all repos
$ just repoupdater list

# Clone all research repos into research/, or pull if already cloned
$ just repoupdater update

# In each repo, check out a new branch
# Note that -- is required to stop argparse treating -b as argument to repoupdater.py
$ just repoupdater exec -- git checkout -b fix-suppression-codelists

# Update codelists.txt (could just use sed)
$ just repoupdater exec -- sed -i s/suppresion/suppression/ codelists/codelists.txt

# Update study definitions (need to use sed, for wildcard support)
$ sed -i s/suppresion/suppression/ research/*/analysis/*.py

# Add, commit, push
# Note that if nothing has been added, the commit will error -- ignore this
$ just repoupdater exec git add .
$ just repoupdater exec -- git commit -m "Fix typo in codelist name"
$ just repoupdater exec -- git push -u origin fix-suppression-codelists

# Create PRs
# Note that errors will be reported for repos where nothing has changed
$ just repoupdater pull-request fix-suppression-codelists "Fix typo in codelist name"
```
