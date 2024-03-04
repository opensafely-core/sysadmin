---
name: TPP reboot
about: Handling
title: "[TPP reboot]"
labels: ''
assignees: pipeline-team

---

Checklist for TPP reboot, to be created when TPP inform us of a maintenance window:



Preparation:

 - [ ] bring window start forward 10min, and extend window close by 30min, as TPP can be a bit optimistic about how long they need
 - [ ] schedule [maintenance window](https://support.freshstatus.io/en/support/solutions/articles/50000001851-how-to-create-a-planned-maintenance-incident-) in freshstatus
 - [ ] communicate advance notice of window to users on #opensafely and #opensafely-users channel
 - [ ] set reminder for window start

When window starts:
 - [ ] stop job runner
 - [ ] gracefully kill jobs

See the [preparing for reboot](https://github.com/opensafely-core/backend-server/blob/main/playbook.md#preparing-for-reboot) section of the playbook for how to do this.

These commands can also be scheduled in advance if the maintenance window is out of hours, see the [planned maintenance](https://github.com/opensafely-core/backend-server/blob/main/playbook.md#planned-maintenance) section for more details.

When window closes:
 - [ ] Check the VM is up and you can SSH in
   - If not chase TPP via email for an update.
   - It is likely they have not finished maintenance yet, if so you may need to extend window and communicate to users.

When the VM is back up:
 - [ ] Is docker up? run `docker ps` on the VM
 - [ ] Is job-runner up? [check status](https://jobs.opensafely.org/status/), or `sudo systemctl status jobrunner`

If Level 4 was rebooted:
 - [ ] [manually start release hatch on the level 4 VM](https://bennettinstitute-team-manual.pages.dev/tech-group/playbooks/opensafely-tpp-level-4/#release-hatch)
   - Note: once we've got the releases UI this will not be necessary

Finally
 - [ ] close window on freshstatus if still active.
