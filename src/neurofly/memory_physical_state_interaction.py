from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any

from .compartment_plasticity_diagnostic import _plastic_edge_state
from .event_local_reinforcement_pulse import _build_pre_event_checkpoint, _restore_recentered
from .learning_control_study import _sha256_file
from .memory_history_expression_bridge import (
    _build_memory_pair,
    _clear_for_recall,
    _population_step,
    _state_difference,
    _terminal_summary,
)
from .memory_trace_reconstruction_audit import _record_three_tau_trajectory
from .smoke import _digest_json

CONFIG_SCHEMA = "neurofly-memory-physical-state-interaction-v0.1"
RECEIPT_SCHEMA = "neurofly-memory-physical-state-interaction-receipt-v0.1"
STATUS = "PREREGISTERED_EXPLORATORY_EXECUTION"
SCOPE = "real-malecns-reward-memory-physical-state-interaction"
EXPECTED_CONDITIONS = (
    "intact",
    "coherent_scheduler_rebuild",
    "clear_vg_adaptation",
    "clear_input_delay",
    "clear_broad_physical_transient",
)
EXPECTED_REPLICATES = (("PI1",3607),("PI2",3613),("PI3",3617),("PI4",3623))
FULL_HISTORY_DECISIONS=60
TERMINAL_DECISIONS=20
POST_REWARD_DELAY_DECISIONS=5
CHANGED_TOLERANCE=1e-12
CLAIM_KEYS={
    "learning_validated","temporal_cue_index_confirmed","prefix_sequence_specificity_confirmed",
    "transient_state_carrier_confirmed","memory_expression_causal",
    "replacement_confirmatory_authorized","behavioral_promotion_authorized",
}

def _array_digest(value:Any)->str:
    import numpy as np
    a=np.ascontiguousarray(value)
    h=hashlib.sha256(); h.update(str(a.dtype).encode()); h.update(json.dumps(list(a.shape)).encode()); h.update(a.tobytes())
    return h.hexdigest()

def _snapshot(inner:Any)->dict[str,Any]:
    b=inner.brain
    return {
        "fields":{k:_array_digest(getattr(b,k)) for k in b.fields},
        "cursor":int(b.cursor),
        "sim_ms":float(b.sim_ms),
        "memory":_plastic_edge_state(inner)["fraction_digest"],
    }

def validate_config(config:dict[str,Any])->dict[str,bool]:
    runtime=config.get("runtime") or {}
    claims=config.get("claim_policy") or {}
    cond=tuple(x.get("id") for x in runtime.get("conditions",[]) if isinstance(x,dict))
    reps=tuple((x.get("id"),x.get("trajectory_seed")) for x in config.get("replicates",[]) if isinstance(x,dict))
    return {
        "schema_exact":config.get("schema")==CONFIG_SCHEMA,
        "status_exact":config.get("status")==STATUS,
        "scope_exact":config.get("scope")==SCOPE,
        "conditions_exact":cond==EXPECTED_CONDITIONS,
        "replicates_exact":reps==EXPECTED_REPLICATES,
        "boundary_exact":runtime.get("boundary")=="after source lag -21 and before source lag -20",
        "window_exact":runtime.get("primary_comparison_window")=="common terminal replay lags -20 through 0 inclusive",
        "frozen_recall":runtime.get("recall_plasticity_frozen") is True and runtime.get("recall_external_reinforcement")=="none",
        "interaction_frozen":(
            (config.get("interaction_analysis") or {}).get("subsystem_a")=="clear_vg_adaptation"
            and (config.get("interaction_analysis") or {}).get("subsystem_b")=="clear_input_delay"
            and (config.get("interaction_analysis") or {}).get("combined")=="clear_broad_physical_transient"
            and (config.get("interaction_analysis") or {}).get("descriptive_interaction_contrast")
                =="combined - subsystem_a - subsystem_b + intact"
            and (config.get("interaction_analysis") or {}).get("no_formal_significance_threshold") is True
        ),
        "claims_locked":set(claims)==CLAIM_KEYS and all(v is False for v in claims.values()),
    }

def _rebuild_scheduler(inner:Any)->dict[str,Any]:
    import numpy as np
    b=inner.brain
    before=_snapshot(inner)
    old_cursor=int(b.cursor)
    slots=int(b.queue_count.shape[0])

    q=b.queue.copy()
    qc=b.queue_count.copy()
    for k in range(slots):
        src=(old_cursor+k)%slots
        b.queue[k,:]=q[src,:]
        b.queue_count[k]=qc[src]

    b.last[:] = b.last - old_cursor
    b.eligibility_last[:] = b.eligibility_last - old_cursor
    b.modulation_last[:] = b.modulation_last - old_cursor

    gap=-45.0-b.rest
    can_fire=(b.v>-45.0) | (b.drive>gap) | ((b.drive+b.g)>gap)
    indices=np.flatnonzero(can_fire).astype(np.int32)
    b.active[:] = 0
    b.active_flag[:] = 0
    b.active[:len(indices)] = indices
    b.active_flag[indices] = 1
    b.nactive[:] = len(indices)

    b.cursor=0
    b.sim_ms=0.0

    after=_snapshot(inner)
    protected={"v","g","refractory","drive","previous_drive","luminance","adaptation","rate_kc","rate_dan","memory_u","memory_w"}
    changed={k for k in before["fields"] if before["fields"][k]!=after["fields"][k]}
    if any(before["fields"][k]!=after["fields"][k] for k in protected):
        raise RuntimeError("Scheduler rebuild changed protected physical state")
    if before["memory"]!=after["memory"]:
        raise RuntimeError("Scheduler rebuild mutated synaptic memory")
    allowed={"queue","queue_count","active","active_flag","nactive","last","eligibility_last","modulation_last"}
    if not changed.issubset(allowed):
        raise RuntimeError(f"Scheduler rebuild changed unexpected fields: {sorted(changed-allowed)}")
    return {"condition":"coherent_scheduler_rebuild","changed_fields":sorted(changed),"old_cursor":old_cursor,"new_cursor":0,"physical_state_preserved":True,"memory_preserved":True}

def _clear_fields(inner:Any,condition:str)->dict[str,Any]:
    b=inner.brain
    fields={
        "clear_vg_adaptation":("v","g","adaptation"),
        "clear_input_delay":("luminance","refractory","queue","queue_count"),
        "clear_broad_physical_transient":("v","g","adaptation","luminance","refractory","queue","queue_count"),
    }[condition]
    before=_snapshot(inner)
    for k in fields:
        getattr(b,k)[:] = b.initial[k]
    after=_snapshot(inner)
    changed={k for k in before["fields"] if before["fields"][k]!=after["fields"][k]}
    if not changed.issubset(set(fields)):
        raise RuntimeError(f"Composite clear changed unexpected fields: {sorted(changed-set(fields))}")
    if before["memory"]!=after["memory"]:
        raise RuntimeError("Composite clear mutated synaptic memory")
    return {"condition":condition,"target_fields":list(fields),"changed_fields":sorted(changed),"memory_preserved":True}

def _apply(inner:Any,condition:str)->dict[str,Any]:
    if condition=="intact":
        return {"condition":"intact","changed_fields":[],"memory_preserved":True}
    if condition=="coherent_scheduler_rebuild":
        return _rebuild_scheduler(inner)
    return _clear_fields(inner,condition)

def _replay_rows(*,none_inner,true_inner,rows,start_lag,reward_pre,changed_mask,paired_delta):
    import numpy as np
    reward_pre=np.asarray(reward_pre,dtype=np.int64)
    changed=np.asarray(changed_mask,dtype=bool)
    delta=np.asarray(paired_delta,dtype=np.float64)
    unique_changed_pre=np.unique(reward_pre[changed])
    changed_l1=float(np.abs(delta[changed]).sum())
    out=[]
    for offset,row in enumerate(rows):
        lag=start_lag+offset
        nd=none_inner.decide(row["frame"],"none",context=copy.deepcopy(row["context"]))
        td=true_inner.decide(row["frame"],"none",context=copy.deepcopy(row["context"]))
        if float(nd.telemetry.get("stimulus_ms") or 0.0)!=0.0 or float(td.telemetry.get("stimulus_ms") or 0.0)!=0.0:
            raise RuntimeError("Recall delivered external reinforcement")
        ns=_population_step(none_inner); ts=_population_step(true_inner)
        nc=ns["counts"]; tc=ts["counts"]
        active_kc=(nc[unique_changed_pre]>0)|(tc[unique_changed_pre]>0)
        active_edges=changed & ((nc[reward_pre]>0)|(tc[reward_pre]>0))
        active_l1=float(np.abs(delta[active_edges]).sum())
        out.append({
            "lag":lag,
            "changed_presynaptic_kc_active_count":int(active_kc.sum()),
            "changed_presynaptic_kc_active_fraction":round(float(active_kc.sum())/len(unique_changed_pre),12),
            "changed_reward_l1_engaged_fraction":round(active_l1/changed_l1,12) if changed_l1 else 0.0,
            "none_action":nd.action,"true_action":td.action,"action_diverged":nd.action!=td.action,
            **_state_difference(ns,ts),
        })
    return out

def _run_condition(*,condition,pre_event_checkpoint,event,delay_rows,prefix_rows,terminal_rows,reward_pre,changed_mask,paired_delta):
    ni,n,ti,t=_build_memory_pair(pre_event_checkpoint=pre_event_checkpoint,event=event,delay_rows=delay_rows)
    _clear_for_recall(ni); _clear_for_recall(ti)
    nm=_plastic_edge_state(ni)["fraction_digest"]; tm=_plastic_edge_state(ti)["fraction_digest"]
    prefix=_replay_rows(none_inner=ni,true_inner=ti,rows=prefix_rows,start_lag=-60,reward_pre=reward_pre,changed_mask=changed_mask,paired_delta=paired_delta)
    nb=_apply(ni,condition); tb=_apply(ti,condition)
    terminal_rows_out=_replay_rows(none_inner=ni,true_inner=ti,rows=terminal_rows,start_lag=-20,reward_pre=reward_pre,changed_mask=changed_mask,paired_delta=paired_delta)
    terminal=_terminal_summary(terminal_rows_out)
    if nm!=_plastic_edge_state(ni)["fraction_digest"] or tm!=_plastic_edge_state(ti)["fraction_digest"]:
        raise RuntimeError("Frozen recall mutated synaptic memory")
    return {
        "condition":condition,"none_intervention":nb,"true_intervention":tb,
        "prefix_lags":[x["lag"] for x in prefix],"terminal":terminal,"memory_unchanged":True,
        "post_delay_fraction_digests":{"none":n["fraction_digest"],"true":t["fraction_digest"]},
    }

def _run_replicate(*,replicate_id,trajectory_seed,base_checkpoint,rep_dir):
    import numpy as np
    rep_dir.mkdir(parents=True,exist_ok=True)
    trajectory,driver,event_index=_record_three_tau_trajectory(base_checkpoint=base_checkpoint,driver_checkpoint=rep_dir/"trajectory-driver.npz",trajectory_seed=trajectory_seed)
    if event_index<FULL_HISTORY_DECISIONS: raise RuntimeError("Event lacks full history")
    event=trajectory[event_index]
    prefix_rows=trajectory[event_index-60:event_index-20]
    terminal_rows=trajectory[event_index-20:event_index+1]
    delay_rows=trajectory[event_index+1:event_index+1+POST_REWARD_DELAY_DECISIONS]
    pre_event_checkpoint=rep_dir/"pre-event.npz"
    pre=_build_pre_event_checkpoint(trajectory=trajectory,event_index=event_index,base_checkpoint=base_checkpoint,pre_event_checkpoint=pre_event_checkpoint)
    _,rn,_,rt=_build_memory_pair(pre_event_checkpoint=pre_event_checkpoint,event=event,delay_rows=delay_rows)
    pre_inner=_restore_recentered(pre_event_checkpoint); c=pre_inner.brain.circuit
    reward_count=len(c["reward"]); reward_mask=np.any(np.abs(c["gain"][:reward_count])>0.0,axis=0)
    reward_pre=np.asarray(c["pre"],dtype=np.int64)[reward_mask]
    paired_delta=np.asarray(rt["post_delay_fraction"])[reward_mask]-np.asarray(rn["post_delay_fraction"])[reward_mask]
    changed=np.abs(paired_delta)>CHANGED_TOLERANCE
    if not np.any(changed): raise RuntimeError("No changed reward edges")
    ref={"none":rn["fraction_digest"],"true":rt["fraction_digest"]}
    conditions={}
    for condition in EXPECTED_CONDITIONS:
        result=_run_condition(condition=condition,pre_event_checkpoint=pre_event_checkpoint,event=event,delay_rows=delay_rows,prefix_rows=prefix_rows,terminal_rows=terminal_rows,reward_pre=reward_pre,changed_mask=changed,paired_delta=paired_delta)
        if result["post_delay_fraction_digests"]!=ref: raise RuntimeError("Paired memory differs across conditions")
        conditions[condition]=result
    return {
        "replicate_id":replicate_id,"trajectory_seed":trajectory_seed,"event_index":event_index,
        "trajectory_digest":driver["trajectory_digest"],"pre_event_checkpoint_sha256":pre["pre_event_checkpoint_sha256"],
        "changed_reward_edge_count":int(changed.sum()),"conditions":conditions,
    }

def _aggregate(reps):
    out={"replicate_count":len(reps),"mean_changed_reward_edge_count":round(mean(r["changed_reward_edge_count"] for r in reps),8),"conditions":{}}
    for condition in EXPECTED_CONDITIONS:
        terminals=[r["conditions"][condition]["terminal"] for r in reps]
        per_lag=[]
        for lag in range(-20,1):
            rows=[next(x for x in t["per_lag"] if x["lag"]==lag) for t in terminals]
            per_lag.append({
                "lag":lag,
                "mean_changed_kc_active_fraction":round(mean(x["changed_presynaptic_kc_active_fraction"] for x in rows),12),
                "mean_changed_l1_engaged_fraction":round(mean(x["changed_reward_l1_engaged_fraction"] for x in rows),12),
                "mbon07_state_difference_fraction":round(sum(x["any_mbon07_state_difference"] for x in rows)/len(rows),12),
                "mbon07_spike_difference_fraction":round(sum(x["mbon07_total_spike_delta"]!=0 for x in rows)/len(rows),12),
                "action_divergence_fraction":round(sum(x["action_diverged"] for x in rows)/len(rows),12),
            })
        out["conditions"][condition]={
            "replicates_with_changed_kc_activity":sum(t["any_changed_kc_activity"] for t in terminals),
            "replicates_with_mbon07_state_difference":sum(t["any_mbon07_state_difference"] for t in terminals),
            "replicates_with_mbon07_spike_difference":sum(t["any_mbon07_spike_difference"] for t in terminals),
            "replicates_with_action_divergence":sum(t["any_action_divergence"] for t in terminals),
            "reward_cue_action_divergence_fraction":round(sum(t["reward_cue_action_divergence"] for t in terminals)/len(terminals),12),
            "mean_changed_kc_active_fraction":round(mean(x["mean_changed_kc_active_fraction"] for x in per_lag),12),
            "mean_changed_l1_engaged_fraction":round(mean(x["mean_changed_l1_engaged_fraction"] for x in per_lag),12),
            "mean_mbon07_state_difference_fraction":round(mean(x["mbon07_state_difference_fraction"] for x in per_lag),12),
            "mean_mbon07_spike_difference_fraction":round(mean(x["mbon07_spike_difference_fraction"] for x in per_lag),12),
            "mean_action_divergence_fraction":round(mean(x["action_divergence_fraction"] for x in per_lag),12),
            "per_lag":per_lag,
        }
    metrics=(
        "mean_changed_kc_active_fraction",
        "mean_changed_l1_engaged_fraction",
        "mean_mbon07_state_difference_fraction",
        "mean_mbon07_spike_difference_fraction",
        "mean_action_divergence_fraction",
        "reward_cue_action_divergence_fraction",
    )
    intact=out["conditions"]["intact"]
    a=out["conditions"]["clear_vg_adaptation"]
    b=out["conditions"]["clear_input_delay"]
    ab=out["conditions"]["clear_broad_physical_transient"]
    out["interaction_contrasts"]={
        metric:round(ab[metric]-a[metric]-b[metric]+intact[metric],12)
        for metric in metrics
    }
    return out

def run_study(*,config_path,base_checkpoint,output_dir,receipt_path):
    config=json.loads(config_path.read_text()); cg=validate_config(config)
    if not all(cg.values()): raise ValueError("Physical-state interaction config failed validation")
    before=_sha256_file(base_checkpoint); output_dir.mkdir(parents=True,exist_ok=True)
    reps=[_run_replicate(replicate_id=i,trajectory_seed=s,base_checkpoint=base_checkpoint,rep_dir=output_dir/i) for i,s in EXPECTED_REPLICATES]
    after=_sha256_file(base_checkpoint)
    eg={
        "source_checkpoint_unchanged":before==after,
        "all_replicates_executed":len(reps)==4,
        "all_memory_frozen":all(r["conditions"][c]["memory_unchanged"] for r in reps for c in EXPECTED_CONDITIONS),
        "all_prefix_lags_exact":all(r["conditions"][c]["prefix_lags"]==list(range(-60,-20)) for r in reps for c in EXPECTED_CONDITIONS),
        "all_terminal_lags_exact":all(r["conditions"][c]["terminal"]["terminal_lags"]==list(range(-20,1)) for r in reps for c in EXPECTED_CONDITIONS),
        "scheduler_physical_state_preserved":all(
            r["conditions"]["coherent_scheduler_rebuild"]["none_intervention"]["physical_state_preserved"] and
            r["conditions"]["coherent_scheduler_rebuild"]["true_intervention"]["physical_state_preserved"] for r in reps
        ),
        "claims_remain_locked":all(v is False for v in config["claim_policy"].values()),
    }
    valid=all(cg.values()) and all(eg.values())
    body={
        "schema":RECEIPT_SCHEMA,
        "status":"EXPLORATORY_MEMORY_PHYSICAL_STATE_INTERACTION_COMPLETE" if valid else "INVALID_EXECUTION",
        "scope":SCOPE,"execution_valid":valid,"config_gates":cg,"evidence_gates":eg,
        "source_checkpoint_sha256":before,"source_checkpoint_sha256_after":after,
        "replicates":reps,"aggregate":_aggregate(reps),
        "learning_validated":False,"temporal_cue_index_confirmed":False,
        "prefix_sequence_specificity_confirmed":False,"transient_state_carrier_confirmed":False,
        "memory_expression_causal":False,"replacement_confirmatory_authorized":False,
        "behavioral_promotion_authorized":False,"production_checkpoint_mutated":False,
        "human_science_review_required":True,
    }
    body["receipt_sha256"]=_digest_json(body)
    receipt_path.parent.mkdir(parents=True,exist_ok=True); tmp=receipt_path.with_suffix(receipt_path.suffix+".partial")
    tmp.write_text(json.dumps(body,indent=2,sort_keys=True)+"\n"); tmp.replace(receipt_path)
    return body

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="data/memory_physical_state_interaction_v01.json")
    p.add_argument("--base-checkpoint",required=True); p.add_argument("--output-dir",required=True); p.add_argument("--receipt",required=True)
    a=p.parse_args(argv)
    r=run_study(config_path=Path(a.config),base_checkpoint=Path(a.base_checkpoint),output_dir=Path(a.output_dir),receipt_path=Path(a.receipt))
    print(json.dumps({"schema":r["schema"],"status":r["status"],"execution_valid":r["execution_valid"],"aggregate":r["aggregate"],"receipt_sha256":r["receipt_sha256"]},indent=2,sort_keys=True))
    return 0 if r["execution_valid"] else 1

if __name__=="__main__":
    raise SystemExit(main())
