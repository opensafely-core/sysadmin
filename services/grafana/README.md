# Grafana deployment instructions
## Create app

```bash
dokku$ dokku apps:create grafana
dokku$ dokku domains:add grafana dashboards.opensafely.org
dokku$ dokku git:set grafana deploy-branch main
dokku$ dokku builder-dockerfile:set grafana dockerfile-path services/grafana/Dockerfile
```

## Create postgresql db for grafana

* on DO db cluster
  * postgresql version to match target server - currently 14 on dokku3

## create persistent storage

```bash
# dokku will create this with uid:gid as 32767:32767 & then the container will be unable to write
dokku$ dokku storage:ensure-directory grafana
dokku storage:mount grafana /var/lib/dokku/data/storage/grafana:/var/lib/grafana

# the grafana container runs as uid 472 (grafana)
# the other dokku containers on dokku3 run as uid 1013 (dokku)
# let's tell the container to run as 1013, then we can use the same file permissions 
dokku$ dokku docker-options:add grafana deploy "--user 1013"
dokku$ dokku docker-options:add grafana run "--user 1013"
myuser$ sudo chown -R dokku:dokku /var/lib/dokku/data/storage/grafana

dokku$ dokku storage:mount grafana /var/lib/dokku/data/storage/grafana:/var/lib/grafana
```

## Configure app

```bash
dokku config:set grafana GF_DATABASE_TYPE="postgres"
dokku config:set grafana GF_DATABASE_HOST="xxx:5432"
dokku config:set grafana GF_DATABASE_NAME="grafana"
dokku config:set grafana GF_DATABASE_USER="grafana"
dokku config:set grafana GF_DATABASE_PASSWORD="xxx"
dokku config:set grafana GF_DATABASE_SSL_MODE="require"
dokku config:set grafana GF_SERVER_ROOT_URL="https://dashboards.opensafely.org/"
```

## Manually pushing

* set up key on target server
  * madwort adding his regular key for now - needs a better setup

```bash
local$ git clone git@github.com:opensafely-core/sysadmin.git
local$ cd sysadmin
local$ git remote add dokku dokku@MYSERVER:grafana
local$ git push dokku main
```

## Letsencrypt

```bash
dokku$ dokku ports:add grafana http:80:3000
# TODO: block access to port 3000?
dokku$ dokku letsencrypt:enable grafana
```

## Create postgresql connection in Grafana

### Configure user on postgresql db cluster

* create `grafanareader` user on cluster in DigitalOcean control panel for primary node
* by default `grafanareader` cannot connect to `jobserver` database
* connect to primary node with psql & allow connections:

```sql
GRANT CONNECT ON database jobserver TO grafanareader;
```

* `grafanareader` will still fail with e.g. "db query error: pq: permission denied for table applications_application"
* configure access as required:

```sql
GRANT SELECT ON applications_application, applications_cmoprioritylistpage, applications_commercialinvolvementpage, applications_datasetspage, applications_legalbasispage, applications_previousehrexperiencepage, applications_recordleveldatapage, applications_referencespage, applications_researcherregistration, applications_sharingcodepage, applications_sponsordetailspage, applications_studydatapage, applications_studyfundingpage, applications_studyinformationpage, applications_studypurposepage, applications_teamdetailspage, applications_typeofstudypage, interactive_analysisrequest, jobserver_backend, jobserver_backendmembership, jobserver_job, jobserver_jobrequest, jobserver_org, jobserver_orgmembership, jobserver_project, jobserver_projectmembership, jobserver_publishrequest, jobserver_release, jobserver_releasefile, jobserver_releasefilereview, jobserver_repo, jobserver_report, jobserver_snapshot, jobserver_snapshot_files, jobserver_stats, jobserver_workspace, redirects_redirect TO grafanareader;
CREATE VIEW jobserver_user_grafana AS SELECT id,last_login,is_superuser,username,is_staff,is_active,date_joined,fullname,created_by_id,login_token_expires_at,pat_expires_at,roles FROM jobserver_user;
GRANT SELECT ON jobserver_user_grafana TO grafanareader;
```

### Connect from Grafana

In the Grafana UI:

* Adminstration
* Plugins
* PostgreSQL
* Add new data source
* Enter `Host`, `Database`, `User`, `Password` from DigitalOcean db cluster read-only node `Connection Details`

### Missing datasource

If you import a Dashboard from a JSON file, the visualisations may error with "Could not find datasource $UUID". It is sometimes possible to fix this by some combination of hitting "Run query" & "Refresh", otherwise you could recreate the visulation by copy-pasting SQL etc. 
