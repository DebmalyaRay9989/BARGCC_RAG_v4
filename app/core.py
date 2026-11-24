"""Auditable BARG-CC mechanisms from the accompanying IJSS manuscript.

This implements fixed numerical encodings, not the manuscript's neural training system.
The row-unit block geometry is z=[sqrt(alpha_m)*e_m]_m (Section 4.9).
No assertion of supervised clustering superiority, global K-means optimality, or
calibration of supplied reliability scores is made by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import hashlib
import io
import math
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score
from sklearn.metrics.cluster import contingency_matrix
from scipy.optimize import linear_sum_assignment

MAX_ROWS = 2000
MAX_COLUMNS = 300
MAX_VIEWS = 6
MAX_FEATURES = 240


@dataclass
class DataBundle:
    name: str
    views: list[np.ndarray]
    view_names: list[str]
    mask: np.ndarray
    scores: np.ndarray
    labels: np.ndarray | None
    score_source: str
    fingerprint: str
    preprocessing: str

    @property
    def n(self) -> int:
        return len(self.mask)


def from_csv(contents: bytes, name: str) -> DataBundle:
    """Parse numeric CSV; columns are <view>__<feature>, a__<view>, r__<view>, label.

    Missing-view values can be blank only where the corresponding a__ view is zero.
    We neither impute present missing values nor silently synthesize reliability.
    """
    if len(contents) > 3_000_000:
        raise ValueError('CSV exceeds the 3 MB upload limit')
    if b'\x00' in contents:
        raise ValueError('Binary content is not an allowed CSV')
    try:
        df = pd.read_csv(io.BytesIO(contents), encoding='utf-8-sig')
    except Exception as e:
        raise ValueError(f'Unable to parse UTF-8 CSV: {str(e)[:120]}') from e
    if df.empty or not (8 <= len(df) <= MAX_ROWS):
        raise ValueError(f'CSV must contain 8–{MAX_ROWS} rows')
    if len(df.columns) > MAX_COLUMNS or df.columns.duplicated().any():
        raise ValueError('Too many or duplicate columns')
    names = []
    for col in df.columns:
        if '__' in col and not col.startswith(('a__','r__')):
            prefix = col.split('__', 1)[0]
            if prefix and prefix not in names:
                names.append(prefix)
    if len(names) < 2 or len(names) > MAX_VIEWS:
        raise ValueError('Provide 2–6 view prefixes such as image__0, text__0')
    view_arrays = []
    mask = np.ones((len(df),len(names)), dtype=bool)
    scores = np.ones((len(df),len(names)), dtype=float)
    have_scores = []
    total_d = 0
    for j, v in enumerate(names):
        feat_cols = [c for c in df.columns if c.startswith(v+'__')]
        if not feat_cols or len(feat_cols) > 120:
            raise ValueError(f'{v}: requires 1–120 numeric features')
        total_d += len(feat_cols)
        if 'a__'+v in df:
            a = pd.to_numeric(df['a__'+v], errors='coerce').to_numpy(dtype=float)
            if not np.isfinite(a).all() or not np.isin(a, [0,1]).all():
                raise ValueError(f'a__{v}: presence mask must contain only 0 or 1')
            mask[:,j] = a.astype(bool)
        if 'r__'+v in df:
            r = pd.to_numeric(df['r__'+v], errors='coerce').to_numpy(dtype=float)
            valid = mask[:,j]
            if not np.isfinite(r[valid]).all() or ((r[valid]<0)|(r[valid]>1)).any():
                raise ValueError(f'r__{v}: present-view scores must lie in [0,1]')
            scores[:,j] = np.where(valid, r, 0.5)
            have_scores.append(v)
        arr = df[feat_cols].apply(pd.to_numeric, errors='coerce').to_numpy(dtype=float)
        if not np.isfinite(arr[mask[:,j]]).all():
            raise ValueError(f'{v}: present-view features must be finite numbers')
        arr = np.where(mask[:,j,None], arr, 0.0)
        # Transductive feature normalization, fitted on observed rows only.
        present = arr[mask[:,j]]
        if len(present) < 2:
            raise ValueError(f'{v}: requires at least two observed rows')
        mean = present.mean(axis=0)
        sd = present.std(axis=0)
        sd[sd < 1e-10] = 1.0
        arr = np.where(mask[:,j,None], (arr - mean) / sd, 0.0)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        # A zero norm is not silently claimed to be unit length; all observed
        # rows must have nonzero norm for the exact view-loss identity.
        if np.any((norms[:,0] < 1e-10)&mask[:,j]):
            raise ValueError(f'{v}: observed row has zero norm after scaling; remove constant records')
        arr = np.where(mask[:,j,None], arr / np.maximum(norms,1e-12), 0.0)
        view_arrays.append(arr.astype(float))
    if total_d > MAX_FEATURES:
        raise ValueError('Total numerical feature dimensions exceed 240')
    if (~mask.any(axis=1)).any():
        raise ValueError('All-missing records are unsupported; remove or flag them upstream')
    labels = None
    if 'label' in df:
        col = df['label']
        if col.isna().any() or col.nunique() < 2:
            raise ValueError('External labels must be complete and contain at least two classes')
        labels = col.astype(str).to_numpy()
    score_source = ('user-supplied unvalidated reliability proxies' if have_scores
                    else 'uninformative constant observed-view scores (all 1.0)')
    return DataBundle(name=name[:80],views=view_arrays,view_names=names,mask=mask,
        scores=scores,labels=labels,score_source=score_source,
        fingerprint=hashlib.sha256(contents).hexdigest()[:16],
        preprocessing='Transductive within-upload feature z-scoring and unit L2 normalization; no inductive holdout')


def masked_gate(scores: np.ndarray, mask: np.ndarray, kappa: float) -> np.ndarray:
    if (scores.shape != mask.shape or mask.ndim != 2 or
        not np.isfinite(kappa) or kappa < 0 or not mask.any(axis=1).all()):
        raise ValueError('Invalid scores, masks, or kappa; all-missing is rejected')
    if not np.isfinite(scores[mask]).all() or ((scores[mask]<0)|(scores[mask]>1)).any():
        raise ValueError('Observed reliability must lie in [0,1]')
    logits = np.where(mask, kappa*(2*scores-1), -np.inf)
    exp = np.where(mask, np.exp(logits-np.max(logits,axis=1,keepdims=True)),0.0)
    return exp / exp.sum(axis=1,keepdims=True)


def floor_bound(rho: float, m: int) -> float:
    if m<2 or not (0 < rho <= 1/m):
        raise ValueError('Floor must be in (0, 1/M] for at least two views')
    return .5 * math.log((1/rho-1)/(m-1))


def fuse(bundle: DataBundle, mask: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """One-norm row-normalized separated block fusion used in Eq. (22)."""
    if not np.allclose(np.sum(alpha,axis=1),1.0,atol=1e-9):
        raise ValueError('Invalid weights; must sum to one per row')
    if np.any(alpha[~mask]!=0):
        raise ValueError('Absent views cannot have any weight')
    return np.concatenate([np.sqrt(alpha[:,j:j+1])*v for j,v in enumerate(bundle.views)],axis=1)


def fit_partition(x: np.ndarray, k: int, seed: int=23) -> dict[str,Any]:
    model=KMeans(n_clusters=k,n_init=10,random_state=seed,max_iter=300)
    labels=model.fit_predict(x).astype(int)
    centres=np.stack([x[labels==j].mean(axis=0) for j in range(k)])
    nearest=np.linalg.norm(x[:,None,:]-centres[None,:,:],axis=2).argmin(axis=1)
    # Scikit-learn can stop at max_iter before the final assignment is fixed;
    # do not issue a refit certificate for such a reference.
    stable=bool(np.array_equal(labels,nearest))
    return {'labels':labels,'centres':centres,'lloyd_fixed_point':stable,'inertia':float(model.inertia_)}


def aligned_assignment_agreement(reference:np.ndarray, other:np.ndarray) -> float:
    """Best one-to-one cluster-ID permutation agreement; invariant to arbitrary IDs."""
    if reference.shape!=other.shape or reference.ndim!=1:
        raise ValueError('Expected paired one-dimensional cluster assignments')
    contingency=contingency_matrix(reference,other)
    rows,cols=linear_sum_assignment(-contingency)
    return float(contingency[rows,cols].sum()/len(reference)*100)


def score_partition(bundle: DataBundle, labels: np.ndarray, x: np.ndarray) -> dict[str,Any]:
    r: dict[str,Any]={}
    if bundle.labels is not None:
        r['ARI'] = float(adjusted_rand_score(bundle.labels, labels))
        r['NMI'] = float(normalized_mutual_info_score(bundle.labels, labels))
    else:
        r['ARI'] = None
        r['NMI'] = None
    try:
        r['silhouette']=float(silhouette_score(x,labels,sample_size=min(len(x),500),random_state=23))
    except Exception:
        r['silhouette']=None
    return r


def view_loss_audit(bundle:DataBundle, alpha:np.ndarray, z:np.ndarray, ref:dict,
                    kappa:float, drop_probability:float, seed:int) -> dict[str,Any]:
    if not (0 <= drop_probability <= 0.75):
        raise ValueError('Drop probability must be between 0 and 0.75')
    rng=np.random.default_rng(seed)
    n,m=bundle.mask.shape
    new_mask=bundle.mask.copy()
    eligible=np.flatnonzero(bundle.mask.sum(axis=1)>=2)
    chosen=eligible[rng.random(len(eligible)) < drop_probability]
    for i in chosen:
        present=np.flatnonzero(bundle.mask[i])
        new_mask[i,rng.choice(present)]=False
    alpha_new=masked_gate(bundle.scores,new_mask,kappa)
    z_new=fuse(bundle,new_mask,alpha_new)
    removed=(bundle.mask & ~new_mask)
    q=np.sum(alpha*removed,axis=1)
    # Exact Eq. (22) under fixed retained scores/embeddings and unit-norm blocks.
    eps=np.sqrt(np.maximum(0.,2*(1-np.sqrt(np.maximum(0.,1-q)))))
    actual=np.linalg.norm(z-z_new,axis=1)
    if not np.allclose(eps,actual,atol=1e-7):
        raise AssertionError('Exact dropout law has failed; do not certify')
    labels=ref['labels']; k=len(ref['centres'])
    centres=np.stack([z[labels==j].mean(axis=0) for j in range(k)])
    new_centres=np.stack([z_new[labels==j].mean(axis=0) for j in range(k)])
    eb=np.array([eps[labels==j].mean() for j in range(k)])
    d=np.linalg.norm(z[:,None,:]-centres[None,:,:],axis=2)
    dnew=np.linalg.norm(z_new[:,None,:]-new_centres[None,:,:],axis=2)
    old_nearest=d.argmin(axis=1)
    certificate_applicable=bool(ref['lloyd_fixed_point'] and np.array_equal(old_nearest,labels))
    competing=np.arange(k)[None,:]!=labels[:,None]
    margin=d-d[np.arange(n),labels,None]
    bound=2*eps[:,None]+eb[labels,None]+eb[None,:]
    certified=np.all((margin>bound)|~competing,axis=1) if certificate_applicable else np.zeros(n,dtype=bool)
    nearest_new=dnew.argmin(axis=1)
    unchanged=(nearest_new==labels)
    false=int(np.sum(certified & ~unchanged))
    if false: raise AssertionError('A certified point changed labels after refit')
    dropped=np.any(removed,axis=1)
    retained=~dropped
    rate=lambda indicator,grp: round(float(indicator[grp].mean())*100,2) if grp.any() else None
    return {'probability':drop_probability,'eligible_rows':len(eligible),'dropped_rows':int(dropped.sum()),
        'retained_rows':int(retained.sum()),'certified_rows':int(certified.sum()),
        'certified_all_pct':rate(certified,np.ones(n,dtype=bool)),
        'certified_dropped_pct':rate(certified,dropped),
        'certified_retained_pct':rate(certified,retained),
        'unchanged_all_pct':rate(unchanged,np.ones(n,dtype=bool)),
        'unchanged_dropped_pct':rate(unchanged,dropped),
        'false_certificates':false, 'max_exact_view_loss':float(np.max(eps)),
        'mean_removed_weight':float(np.mean(q[dropped])) if dropped.any() else 0.0,
        'certificate_applicable':certificate_applicable,
        'scope':'One membership-preserving centroid refit; not global optimum or retrained embedding',
        'status':('CERTIFIED_ROWS_EXIST' if certified.any() else 'INCONCLUSIVE'),
        'dropped_rows_details':[{'row':int(i),'removed_mass':round(float(q[i]),6),
                                 'exact_drift':round(float(eps[i]),6),'certified':bool(certified[i]),
                                 'unchanged_observed':bool(unchanged[i])} for i in np.flatnonzero(dropped)[:150]]}


def analyze(bundle: DataBundle, *,k:int=5,kappa:float=0.7520386983881371,
            rho:float=.1,enforce_floor:bool=True,drop_probability:float=.1,
            seed:int=23) -> dict[str,Any]:
    if k<2 or k>min(20,bundle.n//3): raise ValueError('Number of clusters outside valid range')
    if not np.isfinite(kappa) or kappa<0 or kappa>10: raise ValueError('Kappa must lie in [0,10]')
    if not np.isfinite(rho) or rho<=0 or rho>1/bundle.mask.shape[1]:
        raise ValueError(f'Participation floor must lie in (0,1/{len(bundle.view_names)}]')
    if not isinstance(seed,int) or seed<0 or seed>10_000_000:
        raise ValueError('Seed must be between 0 and 10,000,000')
    cap=floor_bound(rho,len(bundle.view_names))
    applied=min(kappa,cap) if enforce_floor else kappa
    messages=[]
    if applied < kappa-1e-10:
        messages.append(f'Gate strength reduced to {applied:.4f} to enforce {rho:.1%} participation floor')
    if not enforce_floor and kappa > cap +1e-10:
        messages.append('Requested gate strength exceeds the configured guaranteed participation floor')
    if bundle.labels is None:
        messages.append('No external labels: ARI and NMI cannot be computed')
    if 'unvalidated' in bundle.score_source:
        messages.append('Provided scores are proxies, not independently calibrated semantic quality')
    if 'uninformative' in bundle.score_source:
        messages.append('Constant reliability scores imply the gated and availability-only weights coincide')
    baseline_a=masked_gate(bundle.scores,bundle.mask,0.)
    gated_a=masked_gate(bundle.scores,bundle.mask,applied)
    baseline_x=fuse(bundle,bundle.mask,baseline_a)
    gated_x=fuse(bundle,bundle.mask,gated_a)
    base=fit_partition(baseline_x,k,seed)
    gated=fit_partition(gated_x,k,seed)
    base_score=score_partition(bundle,base['labels'],baseline_x)
    gate_score=score_partition(bundle,gated['labels'],gated_x)
    audit=view_loss_audit(bundle,gated_a,gated_x,gated,applied,drop_probability,seed+991)
    # 2D visualization: no use of externally supplied labels in fitting PCA.
    xy=PCA(n_components=2,random_state=seed).fit_transform(gated_x)
    denom=np.maximum(np.max(np.abs(xy),axis=0),1e-9)
    xy=(xy/denom).tolist()
    external_delta=(None if bundle.labels is None else round(gate_score['ARI']-base_score['ARI'],5))
    severity='warning' if not audit['certificate_applicable'] else ('good' if audit['false_certificates']==0 else 'danger')
    if external_delta is None:
        advice='Insufficient evidence of semantic superiority: add independent labels and held-out datasets. Keep availability-only as a mandatory comparator.'
    elif external_delta <= 0:
        advice='At this setting, gating does not improve descriptive external ARI. Prefer the simpler availability-only branch pending independent validation.'
    else:
        advice='Gating improves descriptive ARI in this uploaded sample, but do not promote it without repeated held-out evaluation and calibrated quality proxies.'
    notes = [
        'Stability certificates are sufficient, not necessary; an inconclusive record may still remain unchanged.',
        'The audit compares one refit of reference memberships, not fully reoptimized or globally optimal K-means.',
        'Views are treated as supplied numerical embeddings, not neural encoders trained by this application.',
        'All preprocessing and clustering on an upload are transductive/exploratory; not a valid independent accuracy benchmark.',
    ]
    n=bundle.n
    return {
        'dataset':{'name':bundle.name,'rows':n,'views':bundle.view_names,
          'dimensions':[v.shape[1] for v in bundle.views],
          'observed_pct':round(bundle.mask.mean()*100,2),
          'missing_count':int((~bundle.mask).sum()),
          'score_source':bundle.score_source,'fingerprint':bundle.fingerprint,
          'preprocessing':bundle.preprocessing,'has_external_labels':bundle.labels is not None},
        'config':{'k':k,'requested_kappa':kappa,'applied_kappa':round(applied,8),
            'floor':rho,'max_floor_kappa':round(cap,8),'enforce_floor':enforce_floor,
            'dropout_probability':drop_probability,'seed':seed},
        'summary':{'baseline':base_score,'gated':gate_score,
           'delta_ARI':external_delta,
           'mean_view_weights':{nm:round(float(gated_a[:,j][bundle.mask[:,j]].mean()),4)
                             for j,nm in enumerate(bundle.view_names)},
           'min_observed_share':round(float(gated_a[bundle.mask].min()),6),
           'assignment_agreement_pct':round(aligned_assignment_agreement(base['labels'],gated['labels']),2),
           'raw_cluster_id_agreement_pct':round(float((base['labels']==gated['labels']).mean())*100,2),
           'partition_ARI_between_methods':round(float(adjusted_rand_score(base['labels'],gated['labels'])),4),
           'baseline_inertia':round(base['inertia'],4),'gated_inertia':round(gated['inertia'],4),
           'cluster_id_agreement_definition':'Best one-to-one matching; cluster ID numbers are arbitrary',
           'reference_fixed_point':gated['lloyd_fixed_point'], 'status':severity},
        'audit':audit,'scatter':{'xy':xy,'clusters':gated['labels'].tolist(),
            'baseline_clusters':base['labels'].tolist()},
        'warnings':messages,'limitations':notes,'recommendation':advice,
        'provenance':{'method':'BARG-CC masked gate / unit-norm block fusion / one-refit certificate',
            'paper_equations':['gate Eq. (2)','exact mask-switch Eq. (22)','one-refit Eq. (24)'],
            'random_seed':seed,'dataset_sha256_prefix':bundle.fingerprint,
            'input_score_calibrated':False}}
