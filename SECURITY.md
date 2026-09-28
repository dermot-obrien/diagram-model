# Security policy

## Supported versions

Only the latest release receives fixes.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability. Report it privately through GitHub's [private vulnerability reporting](https://github.com/dermot-obrien/diagram-model/security/advisories/new), with the version affected, the steps to reproduce it and the impact you expect. You will get an acknowledgement within five working days.

## What is in scope

This repository ships Agent Skills: instructions an AI agent follows, and scripts it runs on your machine. Report anything that lets a crafted input document, diagram or configuration file make those scripts read, write or execute outside the paths they were given, or make the agent act beyond the task it was asked to do.

Review any skill before you install it, from this repository or any other. `gh skill preview` shows a skill's content without installing it.
