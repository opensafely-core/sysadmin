---
name: TPP reboot
about: Handling
title: "[TPP reboot]"
labels: ''

---

Checklist for TPP reboot




Preparation:

 - [ ] If TPP have inform us of a maintenance window, bring window start
   forward 10min, and extend window close by 30min, as TPP can be a bit
   optimistic about how long they need. If we are rebooting for other reasons,
   decide on window.
 - [ ] communicate advance notice of window to users on #opensafely and
   #opensafely-users Slack channels
 - [ ] set Slack reminder for window start

When window starts:
 - [ ] stop job runner
 - [ ] gracefully kill jobs

See the [preparing for reboot](https://github.com/opensafely-core/backend-server/blob/main/playbook.md#preparing-for-reboot) section of the playbook for how to do this.

Perform reboot
 - [ ] if we are doing the reboot, then run `sudo reboot`. If TPP are stoping the VM, let them do it.

When window closes or the reboot has finished:
 - [ ] Check the VM is up and you can SSH in
   - If TPP initatied, chase TPP via email for an update.
   - It is likely they have not finished maintenance yet, if so you may need to extend window and communicate to users.
   - If we initiated, we have limited options to debug failure, so we'll need to contact TPP to help diagnose.

When the VM is back up:
 - [ ] Is docker up? run `docker ps` on the VM
 - [ ] Is job-runner up? [check status](https://jobs.opensafely.org/status/), or `sudo systemctl status jobrunner`
 - [ ] If there were jobs that got stopped as part of shutdown, check they are running again
Finally
 - [ ] notifiy users that maintenance is completed.
