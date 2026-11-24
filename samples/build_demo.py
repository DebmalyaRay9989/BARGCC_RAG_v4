"""Rebuild illustrative Digits pseudo-view sample; labels are for evaluation only."""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.datasets import load_digits
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

x,y=load_digits(return_X_y=True)
rng=np.random.default_rng(2026)
idx=np.sort(rng.choice(len(x),size=420,replace=False))
x=x[idx]; y=y[idx]
im=x.reshape(-1,8,8)
intensity=np.concatenate([im.sum(axis=1),im.sum(axis=2)],axis=1)
grads=np.concatenate([(im[:,:,1:]-im[:,:,:-1]).reshape(-1,56),
                      (im[:,1:,:]-im[:,:-1,:]).reshape(-1,56)],axis=1)
fragments=[('intensity',intensity),('pixels',x),('gradients',grads)]
columns={}
for name, raw in fragments:
    scaled=StandardScaler().fit_transform(raw)
    v=PCA(n_components=10,svd_solver='full',random_state=2026).fit_transform(scaled)
    for j in range(v.shape[1]):columns[f'{name}__{j:02d}']=v[:,j].round(6)
    # These geometric pseudo-proxies are NOT a trained reliability estimator.
    columns['r__'+name]=np.clip(.5+.2*np.tanh(v[:,0]),0,1).round(5)
    columns['a__'+name]=np.ones(len(x),dtype=int)
columns['label']=y
out=Path(__file__).with_name('digits_three_derived_pseudoviews.csv')
pd.DataFrame(columns).to_csv(out,index=False)
print(out, out.stat().st_size)
