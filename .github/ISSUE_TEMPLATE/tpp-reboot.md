---
name: TPP reboot
about: Handling
title: "[TPP reboot]"
labels: ''
assignees: pipeline-team

---

Checklist for TPP reboot, to be created when TPP inform us of a maintenance window:



Preparation:

 - [ ] bring window start forward 10min, and extend window close by 30min, as TPP can be a bit optimistic about how long they need.
 - [ ] schedule maintenance window in freshstatus (TODO: how?)
 - [ ] communicate advance notice of window to users on #opensafely and #opensafely-users channel (possibly freshstatus may be able to do this for us?)
 - [ ] set reminder for window start (again freshping might be able to do this).

When window starts:
 - [ ] stop job runner: https://github.com/opensafely-core/backend-server/blob/main/jobrunner/playbook.md#startingstopping-the-service
 - [ ] gracefully kill jobs: https://github.com/opensafely-core/backend-server/blob/main/jobrunner/playbook.md#preparing-for-reboot


When window closes:
 - [ ] Check the VM is up and you can SSH in
   - If not chase TPP via email for an update.
   - It is likely they have not finished maintenance yet, if so you may need to extend window and communicate to users.

When the VM is back up:
 - [ ] Is docker up? run `docker ps` on the VM.
 - [ ] Is job-runner up? [check status](https://jobs.opensafely.org/status/), or `sudo systemctl status jobrunner`.
 - [ ] [manually start release hatch on the level 4 VM](https://bennettinstitute-team-manual.pages.dev/tech-group/playbooks/opensafely-tpp-level-4/#release-hatch)
   - Note: once we've got the releases UI this will no be nessecary
 - [ ] manualy start level3/VM rsync (TODO: write this up in playbook)

Finally
 - [ ] close window on freshstatus if still active.
