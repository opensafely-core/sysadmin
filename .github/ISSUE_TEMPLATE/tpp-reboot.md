---
name: TPP reboot
about: Handling
title: "[TPP reboot]"
labels: ''

---

Checklist for TPP reboot




Preparation:

 - [ ] If TPP have informed us of a maintenance window, bring window start
   forward 10min, and extend window close by 30min, as TPP can be a bit
   optimistic about how long they need. If we are rebooting for other reasons,
   decide on reasonable window.
 - [ ] communicate advance notice of window to users on #opensafely and
   #opensafely-users Slack channels
 - [ ] set Slack reminder for window start

When window starts:
 - [ ] follow the controller playbook to [prepare the TPP backend for
   a reboot](https://github.com/opensafely-core/job-runner/blob/main/DEVELOPERS.md#prepare-for-reboot).
   This should kill all running tasks and pause the TPP backend to stop any new jobs.

If TPP has scheduled this window out of hours, these commands can also be
crudely scheduled using sleep. e.g. to sleep 4 hours then run things:

```
dokku4$ sleep $((4*3600)); dokku run rap-controller python manage.py prepare_for_reboot --backend tpp --skip-confirm
```

Note: check playbook for up to date commands to run.


Perform reboot
 - [ ] if we are doing the reboot, then run `sudo reboot` as your user. If TPP are stoping the VM, let them do it.

When window closes or the reboot has finished:
 - [ ] Check the VM is up and you can SSH in
   - If TPP initiated, chase TPP via email for an update.
   - If they have not finished maintenance yet, you may need to extend window and communicate to users.
   - If we initiated, we have limited options to debug reboot failure, so we'll need to contact TPP to help diagnose.

When the VM is back up:
 - [ ] Is the agent up? [check status](https://jobs.opensafely.org/status/)
 - [ ] [Unpause the TPP backend on the controller](https://github.com/opensafely-core/job-runner/blob/main/DEVELOPERS.md#pause-a-backend)
 - [ ] If there were jobs that got stopped as part of shutdown, check they are running again

Finally
 - [ ] notify users that maintenance is completed.
