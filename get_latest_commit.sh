#!/bin/bash
for f in `ls -d research/*`
do
  #printf "#$f\n" >> latest_commit.txt;
  git --git-dir="$f/.git" for-each-ref refs/heads --format='"%(committerdate)","%(refname)"'|sed "s\^\/"$f/",\g" >> latest_commit.csv;
done
