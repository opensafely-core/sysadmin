# How to recover from an OpenSAFELY redaction failure

# Files released to job-server

Files released to job-server can be deleted (via the workspace releases page on job-server) by a 
user with the OutputChecker role.  The reason for the redaction should be recorded in the 
[tracking document](https://docs.google.com/document/d/1RmbyKCjbfSmyHlQTaZMhtU8mGqpDllSWXqN2at3B1KM/edit).


# Files committed to GitHub

This includes files that may have been released to job-server and then pushed to a GitHub repo 
as well as files released using the old `osrelease` process.

## make it safe

* lock down permissions
* make public repos -> private
* temporarily remove external collabs
* edit branch protection to only allow you to push to master temporarily (we
  don't have an easy way to disabling write access as our current GH cron job
  will just re-enable it within the hour).
* check for forks
  * they should be disabled in the opensafely organisation, but best to verify
  * forks will mean that commits may not become dangling, and therefore would not be removed by the cleaning processes in this guide.

## prepare a repository check-out for cleaning
### get id of the bad commit(s)

We will use this at the very end of the process to verify that we were sucessful.

You need to locate all the commits that contain problematic material. This could be one commit that adds a bad file, or a commit that adds bad content to a pre-existing file.

Let's say we've discovered problematic material in the committed file `removed.txt`, so we can start with the git history for that file, e.g.

```bash
tom@MadBook3 test-repo % git log --follow removed.txt 
commit ed174a2e87b1dd7362be4c70817e21faf1b40ab0 (HEAD -> bad-commit, origin/bad-commit)
Author: Tom Ward <tomward@fmail.co.uk>
Date:   Wed Oct 14 15:50:23 2020 +0100

    to remove
```

(`--follow` means that it keeps looking past renames)

#### Check in case the file contents have been stored under another name

You can also search the git history for the blob - this may be useful if e.g.:
* a bad file has been renamed 
  * e.g. file was committed in a directory `/outputs`, and the directory was renamed to `/released_outputs`
* bad file was added and deleted in the past & then re-added recently. 
  * this is unlikely, but we should be thorough

This works on the hash of the content, so will only find *exact* matches for the entire file, but it may be useful for objects such as image files that may be difficult to search for using substrings.

```bash
tom@MadBook3 test-repo % git ls-tree ed174a2e87b1dd7362be4c70817e21faf1b40ab0
100644 blob 345e6aef713208c8d50cdea23b85e6ad831f0449	README.md
100644 blob 08134969dbf97cb4b571e7250f837428e14b5420	removed.txt

tom@MadBook3 test-repo % git mv removed.txt removed2.txt

tom@MadBook3 test-repo % git commit 
[bad-commit a4485c4] Rename bad file
 1 file changed, 0 insertions(+), 0 deletions(-)
 rename removed.txt => removed2.txt (100%)

tom@MadBook3 test-repo % git log removed2.txt
commit a4485c46d56c740e0b25bc63225cb9c0aae86f5b (HEAD -> bad-commit)
Author: Tom Ward <tomward@fmail.co.uk>
Date:   Tue Jan 12 12:06:33 2021 +0000

   Rename bad file

tom@MadBook3 test-repo % git ls-tree a4485c46d56c740e0b25bc63225cb9c0aae86f5b
100644 blob 345e6aef713208c8d50cdea23b85e6ad831f0449	README.md
100644 blob 08134969dbf97cb4b571e7250f837428e14b5420	removed2.txt

tom@MadBook3 test-repo % git log --find-object 08134969dbf97cb4b571e7250f837428e14b5420
commit a4485c46d56c740e0b25bc63225cb9c0aae86f5b (HEAD -> bad-commit)
Author: Tom Ward <tomward@fmail.co.uk>
Date:   Tue Jan 12 12:06:33 2021 +0000

    Rename bad file

commit ed174a2e87b1dd7362be4c70817e21faf1b40ab0 (origin/bad-commit)
Author: Tom Ward <tomward@fmail.co.uk>
Date:   Wed Oct 14 15:50:23 2020 +0100

    to remove

```

#### content search

You can also search for bad commits using substrings, such as:

```bash
tom@MadBook3 test-repo % git log -S "oh noes"
commit ed174a2e87b1dd7362be4c70817e21faf1b40ab0 (origin/bad-commit)
Author: Tom Ward <tomward@fmail.co.uk>
Date:   Wed Oct 14 15:50:23 2020 +0100

    to remove

```

#### other branches

Once we've identified a bad commit, we can find all branches that contain the bad commit:

```bash
tom@MadBook3 test-repo % git branch --contains ed174a2e87b1dd7362be4c70817e21faf1b40ab0
* bad-commit
  main
```

Here, both `bad-commit` and `main` contain the problem.
To make life easier, we can start by deleting all branches that no longer need (e.g. old branches that have since been merged).


## was the branch pushed to Github?

The `osrelease` tool commits the study outputs & pushes the branch to github, so the most likely scenario is that the bad commit was pushed to github. However, if you're sure that the bad commit was *not* pushed to Github, you may be able to skip ahead to "clean repository".

## find all clones & verify if they need to be cleaned

for each clone:

* easiest option: if there is nothing that needs to be kept in the clone -> DELETE

if there are branches that need to be kept:

* verify whether the clone contains the bad data
  * use techniques above - e.g. `git show <BAD_COMMIT_ID>`
* delete as many stale/unnecessary branches as possible
* garbage collect
* verify which branches need to be kept & contain the bad data
  * use techniques above - e.g. `git show <BAD_COMMIT_ID>`
* push all branches that need to be kept to Github, and then pull them all to the one repo that we're going to clean & make the new basis for future repos

## Consider deleting & reconstructing the entire repo

Once you have one repo on your local machine that contains all the branches that you need, you have two possible options:

* delete & re-create the repo 
* attempt to fix the repo in place


## delete & recreate the repo

Note: so far, we have never had to do this, so not 100% sure of all the details

* backup repo
* (verify backup)
* delete repo
* recreate repo issues etc
* skip

## attempt to fix the repo in place

We will attempt to remove the bad commit/data from the repository on github, then clean our local repo & update the 

Github repositories store references to the specific commits referenced in a pull request, so any pull requests that contain the bad commit in their history will need to be repaired/deleted. You can view these references with:

```bash
$ git ls-remote
From git@github.com:opensafely/documentation.git
2d0b87c4648080551996adf863ed765055706325	HEAD
...
d814aa05e9db41d5a449620a9bafffd423c49434	refs/heads/gh-pages
2d0b87c4648080551996adf863ed765055706325	refs/heads/master
...
2d14adafef925debbace425d296a775ee8356062	refs/pull/2/head
f9d172e1e6ea5bda2616066109941dfdc5eb64be	refs/pull/3/head
22153016310f7b7a88b87efde038769110ce346e	refs/pull/4/head
...
```

Check whether a PR contains a bad commit with e.g.

```bash
$ git fetch origin dc1d0961e6377fdac985693e0685e2e0ddc8b86b
$ git log dc1d0961e6377fdac985693e0685e2e0ddc8b86b | grep 2fe85f5d5bbf6fc3c8df451f85d2307fb30819a0
```

Notes:
  * `git fetch <COMMIT_ID>` may be required if the commit is *only* referenced by a pull request, as a local git repo won't fetch it by default if only referenced by a pull request 
  * Hopefully we won't need to do this very often, we could automate this a bit if necessary



### PRs that were merged

Once a pull request is merged, it is not possible for users to re-open the pull request & update the reference. Therefore, if a pull request contains bad commits, you must contact Github Support and ask them to delete the pull request.

You will need to file a request with Github support to do this.

First, figure out which PR branches have the bad commits in. It could be a lot if the bad commit was a while ago.

Record the PR numbers for later use.


### PRs that were not merged

If a pull request was not merged, it is possible to update the reference. You should:

* restore the branch
* re-open the pull request
* ensure the branch is pulled to your one local repository for cleaning
* and pushed back to update the reference after cleaning

If there are multiple pull requests that were created from the same branch name but at different times with different commit ids, this will be more fiddly. You may need to restore/reopen/clean/push each pull request individually.

## Status check!

By this point we should ideally have:

* one local clone of the repository containing all branches/code to be kept
* deleted all other user clones of the repository
* either:
  * deleted any bad merged github PRs & re-opened any bad unmerged github PRs
  * deleted the repo on github

## clean repository

Now we can clean our local clone of the repository.

### just the most recent commit

If you're lucky, you only have one bad commit, and it's the most recent one (it should appear at the top of `git log` if so). For example:

* you generated some study outputs
* you committed them to the repo without redacting
* you immediately realised your mistake

In order to repair this, you should 

DO THIS:

```bash
$ git reset HEAD^ --soft
```

```bash
$ git reset commit-id-before-badness --hard
```

OR DO THIS:

```bash
# EDIT YOUR FILES
$ git commit --amend
```

### multiple branches/deeper in the history

If your bad commit is deeper embedded in the git history, you can use [Github's guide](https://docs.github.com/en/github/authenticating-to-github/removing-sensitive-data-from-a-repository) to clean your local repo.

# finish cleaning Github

* disable branch protection
  * if necessary, disable any automated scripts ensuring branch protection
* force push all branches to GH
* re-enable branch protection
  * if necessary, re-enable any automated scripts ensuring branch protection


## File support ticker to remove the needed PRs

We have to push the the cleaned repo before GH will do this, but once you've done that you can go here:

https://support.github.com/request/remove-data

And select "Remove pull requests". Select the repo, and input the PR numbers you figured out earlier.

This system will create a ticket which is usually actioned within 24hrs without issue.


## if you deleted the repo

* verify the bad commit(s) is(are) not visible
  * e.g. https://github.com/ORG/my-repo/commit/6902dc3 should 404

## if you did not delete the repo

* verify the bad commit(s) is(are) dangling:
  * e.g. https://github.com/ORG/my-repo/commit/6902dc3 should give you a message `This commit does not belong to any branch on this repository, and may belong to a fork outside of the repository.`
* verify that there are no forks of the repository
  * forks should be disabled - however due to the implementation of github forks, if a fork did exist then a commit that has no reference in our repo may never be garbage collected if it has a reference in the forked repo.
* Garbage collect the repository
  * according to this [github community form post from a staff member](https://github.community/t/does-github-ever-purge-commits-or-files-that-were-visible-at-some-time/1944/3), the policy circa 2020 is "we try not to clean up even orphaned items unless requested by a repo owner or admin, but if a git object becomes orphaned, we can’t guarantee that it will be retained forever."
  * Contact Github Support asking them to "garbage collect the repository".
  * I suspect it's not possible to easily discover dangling commits from the repository, but it may be possible to do a parallel brute-force search to locate them.
  * Also, old commit references can survive in logs - for example in the Github Actions log, if the repository has an action that runs on push events. These workflow run logs can be manually deleted through the web interface if necessary, however if the commit has been garbage collected then the commit reference should only lead to a 404.
* verify the bad commit(s) is(are) not visible
  * e.g. https://github.com/ORG/my-repo/commit/6902dc3 should 404

## restore repo permissions

* if the repo was public, you can safely make it public again
* if the repo had external collaborators, you can safely re-add them
* restore any other repo-specific permissions you removed at the start of this process

## follow-up
* audit trail
  * It is not possible to find out any information about who/when a repo was cloned unless we moved to Github Enterprise - see [Github audit log documentation](https://docs.github.com/en/free-pro-team@latest/github/setting-up-and-managing-organizations-and-teams/reviewing-the-audit-log-for-your-organization#git-category-actions)
* follow-up monitoring?
  * hopefully this guide has helped you to completely remove the bad commit, however you may consider checking the repository at a later date to verify that it has not be re-committed to the repo by accident due to (for example) an unknown extra clone repository. 
