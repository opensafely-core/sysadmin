#!/bin/bash
git config --global alias.clone-branches '! git branch -a | sed -n "/\/HEAD /d; /\/master$/d; /remotes/p;" | xargs -L1 git checkout -t'
echo "repository,branch,codelist" > affected_repository_branches.csv
pwd=$PWD
affected_codelists=`\
  cat deltas.csv |\
  cut -f1 -d , |\
  sort  | uniq |\
  sed 's/\//\-/g;s/$/.csv/g;s/^/codelists\//g'`

for r in `find research/* -maxdepth 0 -type d`
    do
    cd "$pwd/$r"
    #git clone-branches
    #git pull --all
    r=`echo "$r" | sed 's/research\///'`
    for c in $affected_codelists
        do
        for b in `git branch | sed 's/*//;s/ //g'`
            do
                echo "s/^/\"$r\",\"$b\",\"/g;s/$/\"/g" >> ../../log.txt
                git ls-tree -r --name-only "$b" -- "$c" | sed "s/^/\"$r\",\"$b\",\"/g;s/$/\"/g" 2>> log.txt 1>> ../../affected_repository_branches.csv
            done
        done
    cd ..
    done