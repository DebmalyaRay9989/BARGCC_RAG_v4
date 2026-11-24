import numpy as np
import pytest
from pathlib import Path
from app.core import from_csv,masked_gate,floor_bound,fuse,fit_partition,analyze
from app.agent import run_agent

SAMPLE=Path(__file__).resolve().parents[1]/'samples/digits_three_derived_pseudoviews.csv'

@pytest.fixture(scope='module')
def data():return from_csv(SAMPLE.read_bytes(),'digits_demo.csv')

def test_gate_missing_zero_and_row_sums():
    r=np.array([[.9,.1,.8],[.4,.7,.6]],float)
    m=np.array([[1,0,1],[0,1,1]],bool)
    a=masked_gate(r,m,.75)
    assert np.all(a[~m]==0)
    np.testing.assert_allclose(a.sum(1),1,atol=1e-12)

def test_empty_mask_rejected():
    with pytest.raises(ValueError,match='all-missing'):
        masked_gate(np.ones((2,3)),np.array([[1,0,1],[0,0,0]],bool),.5)

def test_floor_and_availability_only():
    k=floor_bound(.1,3)
    assert k==pytest.approx(.7520386983881371,rel=1e-10)
    m=np.array([[1,1,1],[1,0,1]],bool)
    a=masked_gate(np.array([[0,1,1],[0.3,0.5,0.9]]),m,k)
    assert a[m].min()>=.1-1e-12
    u=masked_gate(np.zeros((2,3)),m,0.)
    assert u[0].tolist()==pytest.approx([1/3]*3)
    assert u[1].tolist()==pytest.approx([.5,0,.5])

def test_demo_has_three_derived_pseudoviews(data):
    assert data.n==420
    assert len(data.views)==3
    assert np.allclose([np.linalg.norm(v,axis=1).mean() for v in data.views],[1,1,1],atol=1e-7)
    assert data.labels is not None
    assert 'unvalidated' in data.score_source

def test_comparator_is_descriptive(data):
    result=analyze(data,k=10,drop_probability=.1,seed=23)
    assert result['config']['applied_kappa']<=result['config']['max_floor_kappa']+1e-7
    assert result['audit']['false_certificates']==0
    assert result['summary']['baseline']['ARI'] is not None
    assert result['summary']['gated']['NMI'] is not None
    assert result['provenance']['input_score_calibrated'] is False
    assert len(result['scatter']['xy'])==420

def test_score_error_rejected():
    import pandas as pd
    df=pd.DataFrame({'a__a':[1]*8,'a__b':[1]*8,'a__c':[1]*8,
         'a__0':np.arange(8),'b__0':np.arange(8)**2,'c__0':np.arange(8)**3,
         'r__b':[8]*8})
    with pytest.raises(ValueError,match='scores'):
        from_csv(df.to_csv(index=False).encode(),'invalid.csv')

def test_agent_traces(data):
    res=run_agent(data,'Compare baseline, audit view loss and recommend fallback',
       {'k':10,'kappa':.7520386983881371,'rho':.1,'enforce_floor':True,'drop_probability':.1,'seed':23})
    assert res['plan']==['profile','compare','certify','assess']
    assert len(res['trace'])==4
    assert res['decision']['automatically_promoted'] is False
    assert res['decision']['status']=='REVIEW_REQUIRED'

@pytest.mark.parametrize('p',[.0,.1,.25,.5])
def test_exact_loss_and_no_false_certificate(data,p):
    out=analyze(data,k=10,drop_probability=p,seed=345)
    assert out['audit']['false_certificates']==0
    if p==0: assert out['audit']['dropped_rows']==0

def test_unnormalized_masked_row_rejected(data):
    import copy
    changed=copy.copy(data)
    changed.mask=data.mask.copy();changed.mask[0]=False
    with pytest.raises(ValueError):
        masked_gate(changed.scores,changed.mask,.752)

def test_csv_missing_view_does_not_use_missing_feature_values():
    import pandas as pd
    n=12
    df=pd.DataFrame({'alpha__0':np.arange(n,dtype=float)+1,
         'alpha__1':np.arange(n,dtype=float)**2+2,
         'beta__0':np.arange(n,dtype=float)+3,
         'beta__1':np.arange(n,dtype=float)**2+4,
         'a__alpha':[1]*n,'a__beta':[0]+[1]*(n-1),
         'r__alpha':[1.]*n,'r__beta':[float('nan')]+[.6]*(n-1)})
    df.loc[0,'beta__0']=float('nan');df.loc[0,'beta__1']=float('nan')
    bundle=from_csv(df.to_csv(index=False).encode(),'missing.csv')
    assert bundle.mask[0,1] == False
    assert not bundle.views[1][0].any()
    weights=masked_gate(bundle.scores,bundle.mask,.3)
    assert weights[0,1]==0 and weights[0,0]==1
    x=fuse(bundle,bundle.mask,weights)
    assert np.isfinite(x).all()

def test_agent_local_llm_off_by_default(monkeypatch,data):
    from app.llm import optional_explanation
    monkeypatch.delenv('BARG_OLLAMA_MODEL',raising=False)
    explanation=optional_explanation('What should I deploy?',analyze(data,k=10))
    assert explanation['enabled'] is False
    assert explanation['text'] is None
