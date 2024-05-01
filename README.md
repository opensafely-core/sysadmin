# OpenSAFELY Sysadmin Tools

This repository contains the documentation and scripts used to manage
the OpenSAFELY Github organisation's users, teams, repos and
permissions.

Github's organisation features are somewhat limited. Repositories are
flat, no grouping, so each repo needs explicitly adding to a team, at an
explicit permissions level. This makes managing this via the UI
laborious and and error prone.

This repo include config and scripts to manage the teams and repos via
the Github API.

The high level goal to protect against injection of code via github into
any part of the OpenSAFELY systems. To reduce risk, we to separate the
sensitive infrastructure repos out from the ever-growing list of
study repos, and restrict write access to the senstive repos to a
smaller technical team.  As there is no repository grouping, this is
done via explicit config stored in this repo.

There are two teams. Researchers have admin access to all study repos.
Developers have admin access to all protected infrastructure repos, and
are also in Researchers team.

All master/main branches are protected, even for admins. This disables
force-pushes from anywhere.

Additionally, protected repos require code review, and signing. This
prevents pushes to master/main without a review.

# Readonly Classic PATs

At the time this system was impelemented, Github only had classic PATs. And
whilst these supported a readonly scope for public repos, if you wanted private
repo access, you *had* to have write access too. However, it was not acceptable
for job-server or job-runner to have write access.

So, in order to acheive a readonly opensafely org PAT, we:

a) lowered the base permissions for the opensafely org to read (they were admin!)
b) added the machinery described about to elevate approved users permissions to be able to *write*.
c) created an opensafely-readonly bot account, that was *not* included in the machinery above
c) use this bot use to create PATs for job-server and job-runner.

Over time, this readonly user has also been used to create issues in various
private repo, so is also a collaborator on specific repos in ebmdatalab org as well.

# Run

Ensure you have a GH PAT with org admin permissions in `./org-token`

`make manage` will run the command in dryrun mode, printing changes it would have made

`make manage ARGS=--exec` will actually apply the changes.


# Cron Job

The management script is designed to run periodically. However, it uses a very
privileged secret, so it currently runs from Simon's home machine.

Run set up a cronjob yourself, you can use `cronjob.sh`. First, edit the `tokenfile` variable to
point a file with a GH PAT that has admin org permissions.

Then, set it to run every hour at n minutes past the hour via `crontab -e` or similar.
e.g. to run at 17m past each hour:

`17 * * * * /path/to/cronjob.sh >> /path/to/logfile.log 2>&1`

