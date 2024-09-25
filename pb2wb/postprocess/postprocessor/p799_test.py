P799_OK_VALUES = {
        'TEST*1': 'Q14',
        'ANALYTIC*STATUS*1C': 'Q49472',
        'ANALYTIC*STATUS*1DC': 'Q49473',
        'ANALYTIC*STATUS*1F': 'Q49474',
        'ANALYTIC*STATUS*1I': 'Q49475',
        'ANALYTIC*STATUS*1TC': 'Q49476',
        'ANALYTIC*STATUS*1TF': 'Q49477',
        'ANALYTIC*STATUS*2C': 'Q49478',
        'ANALYTIC*STATUS*2I': 'Q49479',
        'BIBLIOGRAPHY*STATUS*1C': 'Q49617',
        'BIBLIOGRAPHY*STATUS*1FC': 'Q49618',
        'BIBLIOGRAPHY*STATUS*1FI': 'Q49619',
        'BIBLIOGRAPHY*STATUS*1I': 'Q49620',
        'BIBLIOGRAPHY*STATUS*2C': 'Q49621',
        'BIBLIOGRAPHY*STATUS*2I': 'Q49622',
        'MS_ED*STATUS*1C': 'Q50708',
        'MS_ED*STATUS*1F': 'Q50709',
        'MS_ED*STATUS*1I': 'Q50710',
        'MS_ED*STATUS*2C': 'Q50711',
        'MS_ED*STATUS*2I': 'Q50712'
      }

s = '''Q43280  !P799   Q14'''
print(s)
l = s.split('\t')
print(l)
l = ['Q43279', '!P799', '"Q14"\n']
#l = ['Q43281', 'P11', '"Fuero de Alarcón"', 'P700', 'Q51074', 'P700', 'Q51070\n']
print(l[2].lstrip('\"').rstrip("\n"'\"'))
print(l)
print(len(l))
if len(l) == 3 and l[1] == '!P799' or l[2].lstrip('\"').rstrip("\n"'\"') in P799_OK_VALUES.values():
    print('going for it')
    if l[1] == 'P799': #or l[2] not in P799_OK_VALUES.values():
        print('false')
else:
  print('true')

