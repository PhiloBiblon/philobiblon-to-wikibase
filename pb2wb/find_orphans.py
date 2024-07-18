import numpy as np
import pandas as pd
import os
import argparse

# Libraries
bibliographies = ['BETA', 'BITAGAP', 'BITECA']

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--choice', default='BETA', choices=bibliographies, help='Specify a choice from the list')

#parser.add_argument("--bib", nargs="+", default="BETA", help="Name of bibliographies to process. Default is BETA.")
args = parser.parse_args()

# Access command line arguments
bibliography = args.choice

# Libraries
bibliographies = ['BETA', 'BITAGAP', 'BITECA']

files = os.listdir(f'../data/raw/{bibliography}/csvs')
print(files)
#tables = []
table_dict = {}
table_names = ['bio', 'ins', 'geo', 'ana', 'ms_ed', 'bib', 'cop', 'lib', 'uni', 'sub']
for name in table_names:
    for file in files:
        if name.upper() in file:
            print(f'Processing read for {bibliography} {name}')
            table_dict[name] = pd.read_csv(f'../data/raw/{bibliography}/csvs/{file}')

bio = table_dict['bio']
ins = table_dict['ins']
geo = table_dict['geo']
ana = table_dict['ana']
ms_ed = table_dict['ms_ed']
bib = table_dict['bib']
cop = table_dict['cop']
lib = table_dict['lib']
uni = table_dict['uni']
sub = table_dict['sub']

def main():
    # Lets get some orphans!
    print("Starting orphans process")
    lib_ = get_orphans(lib, "LIBID")
    bio_ = get_orphans(bio, "BIOID")
    geo_ = get_orphans(geo, "GEOID")
    ins_ = get_orphans(ins, "INSID")
    ana_ = get_orphans(ana, "CNUM")
    ms_ed_ = get_orphans(ms_ed, "MANID")
    bib_ = get_orphans(bib, "BIBID")
    cop_ = get_orphans(cop, "COPID")
    uni_ = get_orphans(uni, "TEXID")

    arrs = [lib_, bio_, geo_, ins_, ana_, ms_ed_, bib_, cop_, uni_]
    names = ["library", "biography", "geography", "institutions", "analytic", "ms_ed", "bibliography", "copies", "uniform_title"]

    orphans = pd.DataFrame()

    for i in np.arange(len(arrs)):
        new = pd.DataFrame({names[i]: arrs[i]})    
        orphans = pd.concat([orphans, new], axis = 1)
    
    orphans.to_csv(f'{bibliography}_orphans.csv')
    inward = remove_inward(sub, "SUBID")
    print(inward)

    # No outward pointing orphans
    geo_o = outward_only(geo, "GEOID")
    ins_o = outward_only(ins, "INSID")
    ana_o = outward_only(ana, "CNUM")
    ms_ed_o = outward_only(ms_ed, "MANID")
    bib_o = outward_only(bib, "BIBID")
    cop_o = outward_only(cop, "COPID")
    uni_o = outward_only(uni, "TEXID")
    sub_o = outward_only(sub, "SUBID")
    bio_o = remove_inward(bio, "BIOID")
    lib_o = remove_inward(lib, "LIBID")

    arrs2 = [lib_o, bio_o, geo_o, ins_o, ana_o, ms_ed_o, bib_o, cop_o, uni_o, sub_o]
    names = ["library", "biography", "geography", "institutions", "analytic", "ms_ed", 
             "bibliography", "copies", "uniform_title", "subject"]

    orphans2 = pd.DataFrame()

    for i in np.arange(len(arrs2)):
        new = pd.DataFrame({names[i]: arrs2[i]})
    
        orphans2 = pd.concat([orphans2, new], axis = 1)
    
    orphans2.to_csv(f'{bibliography}_outward_orphans.csv')

    # No inward pointing orphans
    geo_i = remove_inward(geo, "GEOID")
    ins_i = remove_inward(ins, "INSID")
    ana_i = remove_inward(ana, "CNUM")
    ms_ed_i = remove_inward(ms_ed, "MANID")
    bib_i = remove_inward(bib, "BIBID")
    cop_i = remove_inward(cop, "COPID")
    uni_i = remove_inward(uni, "TEXID")
    sub_i = remove_inward(sub, "SUBID")
    bio_i = remove_inward(bio, "BIOID")
    lib_i = remove_inward(lib, "LIBID")

    arrs3 = [lib_i, bio_i, geo_i, ins_i, ana_i, ms_ed_i, bib_i, cop_i, uni_i, sub_i]
    for arr in arrs3:
        if type(arr) == 'pandas.core.frame.DataFrame':
            arr = arr[0]
        
    len(arrs3)
    names = ["library", "biography", "geography", "institutions", "analytic", "ms_ed", 
         "bibliography", "copies", "uniform_title", "subject"]

    orphans3 = pd.DataFrame()

    for i in np.arange(len(names)):
        new = pd.DataFrame({names[i]: arrs3[i]})    
        orphans3 = pd.concat([orphans3, new], axis = 1)

    orphans3.to_csv(f'{bibliography}_inbound_orphans.csv')

def find_refs(table, id_type):
    
    bio.name = "bio"
    ins.name = "ins"
    geo.name = "geo"
    ana.name = "ana"
    ms_ed.name = "ms_ed"
    bib.name = "bib"
    cop.name = "cop"
    lib.name = "lib"
    uni.name = "uni"
    sub.name = "sub"

    refs = []

    table2 = table.drop([id_type], axis = 1)

    tables = [bio, ins, geo, ana, ms_ed, bib, cop, lib, uni, sub]
    
    for i in np.arange(9):
        if tables[i].name == table.name:
           tables.pop(i)
    
    tables.append(table2)

    for t in tables:
        for column in t.columns: 
            if all([type(t[column].values[i]) != str for i in np.arange(len(t[column]))]):
                t = t.drop([column], axis = 1)
            elif any(t[column].str.contains('BETA ' + id_type.lower()).dropna()): 
                continue
            else: 
                t = t.drop([column], axis = 1) 

        for column in t.columns:
            refs.extend(np.unique(t[column].dropna())) 
            
    return refs

def remove_inward(table, id_type):
    
    refs = find_refs(table, id_type)
    
    ids = np.unique(table[id_type])
    
    orphans = pd.DataFrame(ids)

    for i in np.arange(len(orphans[0])):
        if orphans.iloc[i, 0] in refs:
            orphans.iloc[i,0] = np.nan

    return orphans.dropna()[0]

def remove_outward(table, id_type, orphans):
    
    final_orphans = []
    
    table = table[table[id_type].isin(orphans)]
    #print(table)
    
    for column in table.columns: 
        if all([type(table[column].values[i]) != str for i in np.arange(len(table[column]))]):
            table = table.drop([column], axis = 1)
        elif any(table[column].str.contains('BETA ').dropna()):                 
            continue
        else: 
            table = table.drop([column], axis = 1)
        #print(table)
    
    if table.empty:
        return None
    table = table.groupby(id_type).agg('count')
    
    
    for i in np.arange(table.shape[0]):
        if not any(table.iloc[i, :].values):
            final_orphans = np.append(final_orphans, table.index[i])

    return final_orphans

def get_orphans(table, id_type):
    orphans = remove_inward(table, id_type)
    orphans = remove_outward(table, id_type, orphans)
    return orphans

def outward_only(table, id_type):
    orphans = table[id_type]
    return remove_outward(table, id_type, orphans)

if __name__ == '__main__':
    main()