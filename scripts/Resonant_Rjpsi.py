#from nanoAOD root files, to 1D hd5 files

from mybatch import *

import awkward as awk
import numpy as np
import uproot
from nanoframe import NanoFrame
import os
import particle
import pandas as pd
import uproot_methods
import ROOT

final_dfs = {
    'pf' : pd.DataFrame(),
}

from pdb import set_trace

nprocessed = 0
#loop sui dataset
for dataset in [args.data,args.mc_mu,args.mc_tau,args.mc_x,args.mc_gen]: 
    if(dataset==''):
        continue
    print(" ")
    print("Opening file", dataset)
    f=open(dataset,"r")
    paths = f.readlines()
    final_dfs['pf']=None
    wrong=0
    all_wrong=0
    tot_events=0
    double_ev=0
    for i,fname in enumerate(paths):
        fname= fname.strip('\n')
        if(i%1==0):
            print("Processing file ", fname)
        nf = NanoFrame(fname, )#branches = branches)
        
        # Load the needed collections, NanoFrame is just an empty shell until we call the collections
        evt = nf['event']
        muons = nf['Muon']
        bcands = nf['BTommm']
        hlt = nf['HLT']
        gen= nf['GenPart']
        nprocessed += hlt.shape[0]

        # Attach the objects to the candidates
        bcands['mu1'] = muons[bcands['l1Idx']]
        bcands['mu2'] = muons[bcands['l2Idx']]
        bcands['k'] = muons[bcands['kIdx']]
        bcands['event'] = nf['event']
        bcands['run'] = nf['run']
        bcands['luminosityBlock'] = nf['luminosityBlock']    
        bcands['l_xy_sig'] = bcands.l_xy / np.sqrt(bcands.l_xy_unc)
        
        
        
        #if the dataset is MC I add gen info
        if (dataset!=args.data):
            bcands['mu1_genpdgId'] = gen[bcands.mu1.genPartIdx].pdgId
            bcands['mu2_genpdgId'] = gen[bcands.mu2.genPartIdx].pdgId
            bcands['k_genpdgId'] = gen[bcands.k.genPartIdx].pdgId

            bcands['mu1_mother'] = gen[gen[bcands.mu1.genPartIdx].genPartIdxMother].pdgId
            bcands['mu2_mother'] = gen[gen[bcands.mu2.genPartIdx].genPartIdxMother].pdgId
            bcands['k_mother'] = gen[gen[bcands.k.genPartIdx].genPartIdxMother].pdgId
            bcands['mu1_grandmother'] = gen[gen[gen[bcands.mu1.genPartIdx].genPartIdxMother].genPartIdxMother].pdgId
            bcands['mu2_grandmother'] = gen[gen[gen[bcands.mu2.genPartIdx].genPartIdxMother].genPartIdxMother].pdgId
            bcands['k_grandmother'] = gen[gen[gen[bcands.k.genPartIdx].genPartIdxMother].genPartIdxMother].pdgId
            if (dataset!=args.mc_mu):
                bcands['mu1_bgmother'] =gen[gen[gen[gen[bcands.mu1.genPartIdx].genPartIdxMother].genPartIdxMother].genPartIdxMother].pdgId
                bcands['mu2_bgmother'] =gen[gen[gen[gen[bcands.mu2.genPartIdx].genPartIdxMother].genPartIdxMother].genPartIdxMother].pdgId
                bcands['k_bgmother'] =gen[gen[gen[gen[bcands.k.genPartIdx].genPartIdxMother].genPartIdxMother].genPartIdxMother].pdgId
        

        
        b_selection = (bcands.k.p4.pt > -99)
        x_selection= (bcands.k.p4.pt > -99)

        #Delete the signal from the JpsiX MC
        if (dataset==args.mc_x):
            x_selection= ~ ((bcands.k.genPartIdx>=0) & ( bcands.mu1.genPartIdx>=0) & (bcands.mu2.genPartIdx>=0) & (abs(bcands.mu1_mother) == 443) & (abs(bcands.mu2_mother) == 443) & (abs(bcands.mu1_grandmother) == 541) & (abs(bcands.mu2_grandmother) == 541) & ( (abs(bcands.k_mother)==541) | ( (abs(bcands.k_mother)==15) & (abs(bcands.k_grandmother)== 541))))

        '''
        for i,bb in enumerate(bcands):
            if (len(bb)>0):
                for b in bb:
                    p_mu1 = gen[i][b.mu1.genPartIdx].p4
                    p_mu2 = gen[i][b.mu2.genPartIdx].p4   
                    p_b = gen[i][gen[i][gen[i][b.mu1.genPartIdx].genPartIdxMother].genPartIdxMother].p4 #grandmother
                    pMu1 = ROOT.TLorentzVector()
                    pMu1.SetPtEtaPhiM(p_mu1.pt,p_mu1.eta,p_mu1.phi,p_mu1.mass)
                    pMu2 = ROOT.TLorentzVector()
                    pMu2.SetPtEtaPhiM(p_mu2.pt,p_mu2.eta,p_mu2.phi,p_mu2.mass)
                    pB = ROOT.TLorentzVector()
                    pB.SetPtEtaPhiM(p_b.pt,p_b.eta,p_b.phi,p_b.mass)
                    Q_sq= (pB-pMu1-pMu2) * (pB-pMu1-pMu2)
                    print("Q_sq ",Q_sq)
        '''
        new_lenght= sum(1 for x in bcands[b_selection & x_selection] if len(x)>=1)
        old_lenght= sum(1 for x in bcands if len(x)>=1)

        best_pf_cand = bcands[b_selection & x_selection].svprob.argmax()
        
        #count selected events
        tot_events+=sum(1 for x in bcands[b_selection & x_selection] if len(x)>0)
        #count events with more than one candidate        
        double_ev+=sum(1 for x in bcands[b_selection & x_selection] if len(x)>1)

        #counting of wrong choices between candidates of same event in the mc datasets
        if(dataset==args.mc_mu or dataset==args.mc_tau):
            #list with more than one candidate for event that I fail to choose
            wrong_list=[b for i,bcand in enumerate(bcands[b_selection & x_selection]) if len(bcand)>1 for j,b in enumerate(bcand) if( (b.k.genPartIdx>=0 and b.mu1.genPartIdx>=0 and b.mu2.genPartIdx>=0) and ( abs(b.mu1_grandmother) == 541 and abs(b.mu2_grandmother) == 541) and (abs(b.k_mother)==541 or (abs(b.k_mother)==15 and abs(b.k_grandmother)== 541)) and ( j!=best_pf_cand[i]))]
            
            #list with all the events with more than one candidate, in which all candidates are wrong. 
            #To be subtracted to double_ev 
            all_wrong_list=[ [1 for b in bcand if not ((b.k.genPartIdx>=0 and  b.mu1.genPartIdx>=0 and b.mu2.genPartIdx>=0) and                                                        ( abs(b.mu1_grandmother) == 541 and abs(b.mu2_grandmother) == 541) and (abs(b.k_mother)==541 or (abs(b.k_mother)==15 and abs(b.k_grandmother)== 541)))] for bcand in bcands[b_selection & x_selection] if len(bcand)>1 ]    
        
            wrong+=len(wrong_list)
            all_wrong+=sum(1 for z in all_wrong_list if len(z)==2)

        bcands_pf = (bcands[b_selection & x_selection][best_pf_cand]).flatten()
        dfs = {}

        for name, tab, sel in [
                ('pf', bcands_pf, b_selection & x_selection), 
        ]:
            dfs[name] = pd.DataFrame()
            df = dfs[name]
            df['event'] = tab['event']
            df['run'] = tab['run']
            df['luminosityBlock'] = tab['luminosityBlock']
            df['mu1_mediumID']= tab.mu1.mediumId
            df['mu2_mediumID']= tab.mu2.mediumId
            df['k_tightID']= tab.k.tightId
            df['k_mediumID']=tab.k.mediumId
            df['k_softID']=tab.k.softId
            df['mu1pt'] = tab.mu1.p4.pt
            df['mu2pt'] = tab.mu2.p4.pt
            df['kpt'] = tab.k.p4.pt
            df['mu1mass'] = tab.mu1.p4.mass
            df['mu2mass'] = tab.mu2.p4.mass
            df['kmass'] = tab.k.p4.mass
            df['mu1phi'] = tab.mu1.p4.phi
            df['mu2phi'] = tab.mu2.p4.phi
            df['kphi'] = tab.k.p4.phi
            df['mu1eta'] = tab.mu1.p4.eta
            df['mu2eta'] = tab.mu2.p4.eta
            df['keta'] = tab.k.p4.eta
            df['mu1_isPF'] = tab.mu1.isPFcand
            df['mu2_isPF'] = tab.mu2.isPFcand
            df['k_isPF'] = tab.k.isPFcand
            df['Bcharge'] = tab.charge
            df['Bpt'] = tab.p4.pt
            df['Beta'] = tab.p4.eta
            df['Bphi'] = tab.p4.phi
            df['Bsvprob'] = tab.svprob
            df['Bcos2D'] = tab.cos2D
            df['Blxy_sig'] = (tab.l_xy / tab.l_xy_unc)
            df['Bmll_raw'] = tab.m_jpsi
            df['Bm_miss_sq'] = tab.m_miss_sq
            df['Bmass'] = tab.p4.mass
            df['Bvtx_x'] = tab.vtx_x
            df['Bvtx_y'] = tab.vtx_y
            df['Bvtx_z'] = tab.vtx_z
            df['Bvtx_ex'] = tab.vtx_ex
            df['Bvtx_ey'] = tab.vtx_ey
            df['Bvtx_ez'] = tab.vtx_ez

            df['Bb_iso03'] = tab.b_iso03
            df['Bb_iso04'] = tab.b_iso04
            df['Bk_iso03'] = tab.k_iso03
            df['Bk_iso04'] = tab.k_iso04
            df['Bl1_iso03'] = tab.l1_iso03
            df['Bl1_iso04'] = tab.l1_iso04
            df['Bl2_iso03'] = tab.l2_iso03
            df['Bl2_iso04'] = tab.l2_iso04
            df['BE_mu_star']=tab.E_mu_star
            df['BE_mu_canc']=tab.E_mu_canc
            df['BQ_sq']=tab.Q_sq
            df['Bpt_var']=tab.pt_var
            df['Bpt_miss_vec']=tab.pt_miss_vec
            df['BDR']=tab.DR
            df['nB'] = sel.sum()[sel.sum() != 0]
            if(dataset!=args.data):
                df['Bmu1_mother']=tab.mu1_mother
                df['Bmu2_mother']=tab.mu2_mother
                df['Bk_mother']=tab.k_mother
                df['Bmu1_grandmother']=tab.mu1_grandmother
                df['Bmu2_grandmother']=tab.mu2_grandmother
                df['Bk_grandmother']=tab.k_grandmother
                df['mu1_pdgId'] = tab.mu1.pdgId
                df['mu2_pdgId'] = tab.mu2.pdgId
                df['k_pdgId'] = tab.k.pdgId
                df['mu1_genpdgId'] = tab.mu1_genpdgId
                df['mu2_genpdgId'] = tab.mu2_genpdgId
                df['k_genpdgId'] = tab.k_genpdgId


                if (dataset!=args.mc_mu):
                    df['Bmu1_bgmother']=tab.mu1_bgmother
                    df['Bmu2_bgmother']=tab.mu2_bgmother
                    df['Bk_bgmother']=tab.k_bgmother

        final_dfs['pf'] = pd.concat((final_dfs['pf'], dfs['pf']))
        #print("DFS")
        #print(dfs['pf'])
        #print(" ")
        #print("FINAL")
        #print(final_dfs['pf'])
    print("Total saved events: ", tot_events)
    print("Events with more than one candidate: ",double_ev)
    if(dataset==args.mc_mu or dataset==args.mc_tau):
        print("Wrong choice between two or more candidates of the same event: ",wrong)
        print("Events with all wrong candidates: ", all_wrong)
    print("")
    dataset=dataset.strip('.txt')
    name=dataset.split('/')
    d=name[len(name)-1].split('_')
    final_dfs['pf'].to_hdf('hd5_files/'+d[0]+'_new.h5', 'pf', mode = 'w')
    print("Saved file "+ 'hd5_files/'+ d[0]+'_new.h5')

print('DONE! Processed events: ', nprocessed)