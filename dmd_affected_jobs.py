# %%
import pandas as pd
import numpy as np
# %%
df_jobserver = pd.read_csv('workspace_jobs.csv')
print(f"total job records:{len(df_jobserver.index)}")
# %%
df_jobserver = df_jobserver[df_jobserver.status.str.lower()=='succeeded']
print(f"succeeded job records:{len(df_jobserver.index)}")
df_jobserver['repo'] = df_jobserver['repo'].str.replace('https://github.com/','')
df_jobserver['started_at']=pd.to_datetime(df_jobserver.started_at)
#df_jobserver['started_at'] = df_jobserver['started_at'].dt.date
#%%
df_jobserver = df_jobserver.groupby(['repo','branch']).agg(last_run_time=('started_at',np.max)).reset_index()
print(f"latest run time per workspace:{len(df_jobserver.index)}")
# %%
df_branches = pd.read_csv('oldcodes_allbranches.csv')
print(f"affected code instances in research repos:{len(df_branches.index)}")
# %%
df_vmp = pd.read_gbq('''SELECT
    vpidprev,vpiddt
  FROM
    `ebmdatalab.dmd.vmp_full`
  WHERE
    vpidprev IS NOT NULL''', project_id='ebmdatalab', dialect='standard')

print(f"expired dmd VMP ids:{len(df_vmp.index)}")
# %%
df_best_before=df_vmp.groupby('vpidprev').agg(bbd=('vpiddt',np.max)).reset_index()
print(f"expired dmd VMP best-before dates:{len(df_best_before.index)}")
# %%
df_branches = df_branches.merge(df_best_before,how='inner',left_on='code',right_on='vpidprev')
print(f"instances ∩ best-before:{len(df_branches.index)}")
df_branches = df_branches.groupby(['repository','branch','filename']).agg(bbd=('bbd',np.max)).reset_index()
print(f"max-best-before dates per codelist instance:{len(df_branches.index)}")
# %%
df = df_branches.merge(df_jobserver,how='inner',left_on=('repository','branch'),right_on=('repo','branch'))
print(f"succeeded jobs ∩ codelist best-before dates:{len(df.index)}")
# %%
df_deltas=pd.read_csv('codelist_deltas.tsv',delimiter='\t')
print(f"codelist deltas results:{len(df_deltas.index)}")
# %%
df['codelist']=df['filename'].str.replace('codelists/','').replace('.csv','')
df['codelist']=df['codelist'].str.replace('.csv','')
# %%
df = df.merge(df_deltas,on='codelist',how='inner')
print(f"deltas ∩ succeeded jobs ∩ codelist best-before dates:{len(df.index)}")
# %%
df['bbd'] = pd.to_datetime(df.bbd)
# %%
df = df[(df.last_run_time.dt.date>df.bbd)]
print(f"affected job-codelists:{len(df.index)}")

#%%
df.sort_values('delta%',ascending=False).to_csv('dmd_impact.csv',index=False)
# %%
