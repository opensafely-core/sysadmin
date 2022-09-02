import re
import glob
import json
import pandas as pd

funcs = [r'patients.with_these_clinical_events\('
,r'patients.with_these_medications\('
,r'patients.with_gp_consultations\('
,r'patients.with_vaccination_record\('
,r'patients.with_tpp_vaccination_record\(']

patfuncs = '(?:'+'|'.join(funcs)+')'
pattern_offset=patfuncs+r'(?:[^\)]|\n)*between=\["(\w*)",\s*"\1 +[+-] +(\d+) +(\w+)"'
pattern_sameday=patfuncs+r'(?:[^\)]|\n)*between=\["(\w*)",\s*"\1"'

pyfiles = glob.glob('research/**/**/*definition*.py')

results_sameday={}
results_offset={}

for file in pyfiles:
    with open(file,'r') as f:
        fc = f.read()
        match_offset = re.findall(pattern_offset,fc,re.MULTILINE)
        if match_offset:
            results_offset[file] = match_offset
        match_sameday = re.findall(pattern_sameday,fc,re.MULTILINE)
        if match_sameday:
            results_sameday[file] = match_sameday

with open('report_offset.json','w') as rep:
    json.dump(results_offset,rep,indent=4)
with open('results_sameday.json','w') as rep:
    json.dump(results_sameday,rep,indent=4)

df = pd.DataFrame(columns=['study','file','date','offset_n','offset_period'])
for k,v in results_offset.items():
    for instance in v:
        _,study,_,file = k.split('/')
        date,offset_n,offset_period = instance
        row = {
            'study':study,
            'file':file,
            'date':date,
            'offset_n':offset_n,
            'offset_period':offset_period
            }
        df = df.append(row,ignore_index=True)

df.to_csv('offsets.csv',index=False)

df = pd.DataFrame(columns=['study','file','count'])
for k,v in results_sameday.items():
    _,study,_,file = k.split('/')
    row = {
        'study':study,
        'file':file,
        'count':len(v)
    }
    df = df.append(row,ignore_index=True)

df.to_csv('sameday.csv',index=False)