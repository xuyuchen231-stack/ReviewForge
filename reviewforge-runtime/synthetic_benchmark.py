"""Executed illustrative fed-batch H1-H4 comparison; not PenSim or biological validation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np


def trajectory(condition, feed, dt=.02):
    # Extensive balances: biomass mass, substrate mass, volume.
    state = np.array([1., 12., 1.])
    time = np.arange(0., 24.+dt/2, dt)
    rows = []
    def rhs(y):
        biomass, substrate, volume = y
        concentration = max(substrate/volume, 0.)
        growth = .24*concentration/(.4+concentration)
        return np.array([growth*biomass, feed*120.-growth*biomass/.5, feed])
    for t in time:
        rows.append([t, state[0], state[1], state[2], float(t>=10)*condition])
        k1=rhs(state); k2=rhs(state+dt*k1/2); k3=rhs(state+dt*k2/2); k4=rhs(state+dt*k3)
        state = state+dt*(k1+2*k2+2*k3+k4)/6
    return np.array(rows)


def basis(data, loss=0.):
    t, mass, _, volume, induction = data.T
    a=np.zeros(len(t)); b=np.zeros(len(t))
    # Stable trapezoidal integration of d(VP)/dt = q*VX - k*VP.
    for i in range(1,len(t)):
        dt=t[i]-t[i-1]; decay=np.exp(-loss*dt)
        a[i]=decay*a[i-1]+dt*(mass[i-1]*(induction[i-1]>0)*decay+mass[i]*(induction[i]>0))/2
        b[i]=decay*b[i-1]+dt*(mass[i-1]*induction[i-1]*decay+mass[i]*induction[i])/2
    return np.column_stack([a/volume,b/volume])


def design(data, candidate, loss=0.):
    base=basis(data,loss)
    if candidate=='H1':
        return np.column_stack([.018*base[:,0],np.ones(len(data))])
    if candidate=='H2':
        return base[:,:1]
    return base


def run_benchmark(test_shift=0.):
    protocol={'train':[0,1,2], 'validation':[3,4], 'test':[5,6], 'loss_grid':[0.,.03,.08,.16], 'seed':8127}
    conditions=[.6,1.,1.4,.8,1.2,.7,1.3]
    feeds=[.015,.02,.025,.022,.018,.017,.024]
    data=[trajectory(c,f) for c,f in zip(conditions,feeds)]
    rng=np.random.default_rng(protocol['seed']); metrics=[]; frozen={}; selection={}; trajectories=[]; raw=[]
    scenarios={'calibration_bias':(1.25,0.,0.,.018),'constant_parameter':(1.,0.,0.,.025),
               'condition_dependence':(1.,.012,0.,.012),'formation_and_loss':(1.,.012,.08,.012)}
    for name,(gain,slope,loss,constant) in scenarios.items():
        truth=[gain*(basis(d,loss)@np.array([constant,slope])) for d in data]
        observed=[p+rng.normal(0,.004,len(p)) for p in truth]
        for i in protocol['test']:
            observed[i]=observed[i]+test_shift
        for split in ('train','validation','test'):
            for i in protocol[split]:
                for j in range(0,len(data[i]),25):
                    raw.append({'scenario':name,'split':split,'batch':i,'time':float(data[i][j,0]),'condition':conditions[i],'feed':feeds[i],'synthetic_truth':float(truth[i][j]),'observed':float(observed[i][j])})
        scores={}; frozen[name]={}
        for candidate in ('H1','H2','H3','H4'):
            options=[]
            for k in protocol['loss_grid'] if candidate=='H4' else [0.]:
                x=np.vstack([design(data[i],candidate,k)[::25] for i in protocol['train']])
                y=np.concatenate([observed[i][::25] for i in protocol['train']])
                parameters=np.linalg.lstsq(x,y,rcond=None)[0]
                val=np.concatenate([design(data[i],candidate,k)[::25]@parameters-observed[i][::25] for i in protocol['validation']])
                options.append((float(np.mean(val**2)),k,parameters))
            score,k,parameters=min(options,key=lambda item:item[0])
            frozen[name][candidate]={'loss':k,'parameters':parameters.tolist()}; scores[candidate]=score
            for split in ('train','validation','test'):
                error=np.concatenate([design(data[i],candidate,k)[::25]@parameters-observed[i][::25] for i in protocol[split]])
                metrics.append({'scenario':name,'candidate':candidate,'split':split,'rmse':float(np.sqrt(np.mean(error**2)))})
            for i in protocol['test']:
                prediction=design(data[i],candidate,k)@parameters
                for j in range(0,len(data[i]),25):
                    t,m,s,v,_=data[i][j]
                    trajectories.append({'scenario':name,'candidate':candidate,'batch':i,'time':float(t),'biomass':float(m/v),'substrate':float(s/v),'volume':float(v),'synthetic_truth':float(truth[i][j]),'observed':float(observed[i][j]),'predicted':float(prediction[j])})
        selection[name]=min(scores,key=scores.get)
    return {'experimental_data':False,'kind':'illustrative_synthetic_fedbatch','pensim_replication':False,
            'protocol':protocol,'frozen_models':frozen,'selection':selection,'metrics':metrics,'trajectories':trajectories,'raw_observations':raw,
            'limitations':['Parameters are illustrative and not fitted to a named organism.',
                           'H1 assay gain and H2 formation coefficient can be observationally confounded without independent assay information.',
                           'Selection uses validation only; test trajectories never tune parameters.',
                           'Synthetic model agreement does not establish real-process transfer or prospective control.']}


def export(directory):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    result=run_benchmark()
    for key in ('metrics','trajectories','raw_observations'):
        with (directory/(key+'.csv')).open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(result[key][0]));writer.writeheader();writer.writerows(result[key])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(9,6),layout='constrained')
    for ax,scenario in zip(axes.flat,result['selection']):
        rows=[r for r in result['trajectories'] if r['scenario']==scenario and r['batch']==5]
        actual=[r for r in rows if r['candidate']=='H1']
        ax.plot([r['time'] for r in actual],[r['synthetic_truth'] for r in actual],color='black',label='Synthetic truth')
        for candidate in ('H1','H2','H3','H4'):
            sample=[r for r in rows if r['candidate']==candidate]
            ax.plot([r['time'] for r in sample],[r['predicted'] for r in sample],label=candidate)
        ax.set(title=scenario.replace('_',' '),xlabel='Time (illustrative h)',ylabel='Product (illustrative g/L)')
    axes.flat[0].legend(fontsize=7);fig.suptitle('Executed synthetic benchmark; no experimental cultivation data')
    for suffix in ('pdf','svg','png'):
        fig.savefig(directory/('synthetic_hypotheses.'+suffix),dpi=250)
    plt.close(fig)
    implementation=Path(__file__).read_bytes()
    (directory/'implementation.py').write_bytes(implementation)
    result.pop('trajectories');result.pop('raw_observations'); result['implementation_sha256']=hashlib.sha256(implementation).hexdigest()
    import platform
    result['environment']={'python':platform.python_version(),'numpy':np.__version__}
    result['limitations'].append('Synthetic truth is deliberately contained in the candidate family; this is a protocol demonstration, not an unbiased ranking of general methods.')
    (directory/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); result=export(args.output)
    print(json.dumps({'status':'EXECUTED','experimental_data':False,'selection':result['selection']}))
