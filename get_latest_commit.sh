#!/bin/bash
for f in `ls -d research/*`:
do
  printf "#$f\n" >> latest_commit.txt;
  git --git-dir="$f/.git" log -1 --format=%ci >> latest_commit.txt;
done

