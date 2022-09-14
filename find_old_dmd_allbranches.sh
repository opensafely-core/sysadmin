#!/bin/bash
git config --global alias.clone-branches '! git branch -a | sed -n "/\/HEAD /d; /\/master$/d; /remotes/p;" | xargs -L1 git checkout -t'
echo "repository,branch,filename,code" > oldcodes_allbranches.csv
pwd=$PWD
affected_codes=`cat affected_codes.txt`
for r in `find research/* -type d -maxdepth 0`
    do
    cd "$pwd/$r"
    git clone-branches
    git pull --all
    for c in $affected_codes
        do
        matches=`git grep $c $(git rev-list --all -- codelists/*.csv) -- codelists/*.csv`
        for match in $matches
            do
            commit=`echo "$match"|cut -d : -f1`
            filename=`echo "$match"| cut -d : -f2`
            for b in `git branch --contains "$commit"| sed 's/* //'`
                do
                echo "$r,$b,$filename,$c" >> ../../oldcodes_allbranches.csv
                done
            done
        done
    cd ..
    done