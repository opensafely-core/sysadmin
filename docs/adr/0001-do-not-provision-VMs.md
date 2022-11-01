# 1. Manually provision VM and IPs

Date: 2022-10-31

## Status

Approved

## Context

We need to migrate to new VMs to keep on supported releases.

We want to moving to using declarative tooling rather than the manual ad-hoc
methods we have used in the past

We evaluated both terraform and ansible as ways to declaratively define VMs,
IPs and other base infrastructure.

## Decision

We are not going to use terraform, or anything else, to provision VMs, at least for now.

Terraform is designed for stateless, immutable infrastructure, and ours is not
that. This means it wants to destroy and recreate VMs when things change,
and has no good tools for continuously configuring an already deployed VM.
Thus we we need to also use something like ansible, and if we're doing that,
we might as well use ansible for the provisioning of VMs too, rather than
having two different stacks.

For both Terraform and Ansible, provisioning a new VM or a fixed IP or volume
is a rare event, and is easy enough to do manually, and then manage it with
something else. It's not worth automating this infrequent task currently.


## Consequences

We need to manually create VMs, IPs and any volumes.

We still need to decide on a tool to manage the VMs once they are created,
which is where most of the value is.

