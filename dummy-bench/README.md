# Dummy data benchmarking

This directory contains the historic record of a one-shot dummy benchmarking
run across all ehrql actions.

It was somewhat specific to the specific benchmarking questions, but it preserved here for potential future work.

It was 100% written by Codex. All scripts have --help, and are potentially reusable.

Note: the logs/ and query-models/ directories have not been commited, as that
is 150mb of text data that will bloat the repo somewhat.  All the interesting
data in them has been extracted into `dummy_matches_wide.csv`, which is
committed.


## Requirements:

Needed uv and opensafely-cli installed.

## The Proces

This is a historical record of how the work was done.

### Checkout all projects

Used repoupdater.py from parent directory to checkout all projects.

See `python repoupdater.py --help`. You will need a GH token.

This checked out all current projects into ../research. Did not update them
after doing the first run, so that nothing changed about the users code.

### Find all ehrql:v1 jobs

Found all ehrql:v1 actions and save them.

`uv run find_ehrql_actions.py > ehrql_actions`

### Create a local build of ehrql docker image

In a local ehrql checkout, prepared the changes under test.

Note, that for this benchmarking, ehrql was manually altered to:
 - a) log more timing information
 - b) ignore target size, always try least one batch of 5000, see how many matches we get
 - c) ignore --dummy-tables arguments
 - d) manually switch between hardcoded nextgen and legacy, depending on the benchmarking run

The specific details can be seen in ehrql.patch.

Ran:

```
just build-ehrql
docker image tag ehrql-dev ghcr.io/opensafely-core/ehrql:v1
```

This built a docker image with the changes, and tagged it so that
`opensafely run` will use it.

### Serialized the query model for later

This ran through all the jobs and save the serialized query model. It used
`os_definition.py` as a helper to do it.

Unless the ehrql changes are modifiying the query model, you should only need to do this once.

`uv run run_ehrql_actions ehrql-actions --definition`

The query model json should be saved to `./query-models/{project}/metadata/{action}.json`. 

### For each measurement

There were 5 in total:

 - legacy: generated 1 batch of legacy dummy data
 - nextgen: generated 2 batches of nextgen dummy data (as nextgen has an optimisation for 2nd batch onwards)
 - nextgen-old: used old pre-tomw optimisations to retroactively benchmark the improvements
 - nextgen-tomw2: speculative optimisation changes from tomw
 - tomw3: different speculative optimisation changes from tomw

1. Ran the jobs to generate the log files.

This was done with.
`uv run run_ehrql_actions ehrql-actions`

This ran all the jobs with opensafely-cli. It will take a while. I ran with `--workers 4`, for
4 parallel jobs, and it took ~6h or so.

2. Copid the log files

`uv run copy_metadata_logs.py logs/{measurement_name}`

This preserves the log file for later analysis.

### Extract data from logs

`uv run dummy_logs_to_csv.py`

This has an explicit list of measurements, and parsed all the log files for
each measurement, and all the query model json, and merged it all together into
a single csv file: `dummy_matches_wide.csv`. This contains columns for every
measurement, plus a bunch of other metadata, e.g. project, action, author,
date, query model info, etc.

It filters out jobs that did not succesfully generate dummy data, and puts them
into `dummy_matches_no_batches.csv`. This was done mainly as a diagnosis tool to
ensure that the whole pipeline ran correctly. All the failures in there at the
end were to do with bad ehrql that doesn't run.

### Analyse the csv data

This was done with a marimo notebook:

`uv run marimo run dummy_csv_analysis`

It's a random grab bag of charts and tables designed to answer questions we had.

It has a view of the csv data which is useful for sorting and filtering the data.

It also measures the geometric mean of some performance differences between
specific experiments.
