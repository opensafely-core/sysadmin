log=$(mktemp)
echo "Repo url, commit, author, date"
for r in research/*
do 
    git -C "$r" log --pretty=format:'%h, %an, "%ad"' -S "admitted_to_icu" > "$log"
    url=$(git -C "$r" config --get remote.origin.url | sed 's#git@github.com:#https://github.com/#' | sed 's/\.git$//')
    while IFS= read -r line
    do
        echo "$url, $line"
    done < "$log"
done

