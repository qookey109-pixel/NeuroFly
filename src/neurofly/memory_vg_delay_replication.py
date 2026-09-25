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
from .memory_history_expression_bridge import _build_memory_pair, _clear_for_recall, _terminal_summary
from .memory_physical_state_interaction import _replay_rows
from .memory_trace_reconstruction_audit import _record_three_tau_trajectory
from .smoke import _digest_json

CONFIG_SCHEMA="neurofly-memory-vg-delay-replication-v0.1"
RECEIPT_SCHEMA="neurofly-memory-vg-delay-replication-receipt-v0.1"
STATUS="PREREGISTERED_EXPLORATORY_EXECUTION"
SCOPE="real-malecns-reward-memory-vg-delay-replication"
TARGET_REPLICATES=4
FULL_HISTORY_DECISIONS=60
POST_REWARD_DELAY_DECISIONS=5
CHANGED_TOLERANCE=1e-12
CANDIDATE_POOL=(5407,5413,5417,5419,5431,5437,5441,5443,5449,5471,5477,5479,5483,5501,5503,5507,5519,5521,5527,5531)
VOLATILE_CONTEXT_KEYS={"survival_seconds","total_active_seconds","first_clear_seconds","latest_clear_seconds","best_clear_seconds","seconds"}
EXPECTED_CONDITIONS=(
    "intact",
    "clear_vg_delay",
    "clear_broad_physical_transient",
)
TARGET_FIELDS={
    "intact":(),
    "clear_vg_delay":("v","g","refractory","queue","queue_count"),
    "clear_broad_physical_transient":("v","g","adaptation","luminance","refractory","queue","queue_count"),
}
CLAIM_KEYS={"learning_validated","temporal_cue_index_confirmed","prefix_sequence_specificity_confirmed","transient_state_carrier_confirmed","memory_expression_causal","replacement_confirmatory_authorized","behavioral_promotion_authorized"}
METRICS=(
    "mean_changed_kc_active_fraction",
    "mean_changed_l1_engaged_fraction",
    "mean_mbon07_state_difference_fraction",
    "mean_mbon07_spike_difference_fraction",
    "mean_action_divergence_fraction",
    "reward_cue_action_divergence_fraction",
)

def _stable(value:Any)->Any:
    if isinstance(value,dict):
        return {str(k):_stable(v) for k,v in sorted(value.items(),key=lambda kv:str(kv[0])) if str(k) not in VOLATILE_CONTEXT_KEYS}
    if isinstance(value,list):
        return [_stable(x) for x in value]
    if isinstance(value,tuple):
        return [_stable(x) for x in value]
    return value

def _sensory_digest(rows:list[dict[str,Any]])->str:
    return _digest_json([
        {
            "frame_sha256":hashlib.sha256(row["frame"].tobytes()).hexdigest(),
            "stable_context_sha256":_digest_json(_stable(row["context"])),
        }
        for row in rows
    ])

def validate_config(config:dict[str,Any])->dict[str,bool]:
    sel=config.get("selection") or {}
    runtime=config.get("runtime") or {}
    rep=config.get("replication_analysis") or {}
    claims=config.get("claim_policy") or {}
    conds=tuple(x.get("id") for x in runtime.get("conditions",[]) if isinstance(x,dict))
    fields={x.get("id"):tuple(x.get("target_fields") or ()) for x in runtime.get("conditions",[]) if isinstance(x,dict)}
    return {
        "schema_exact":config.get("schema")==CONFIG_SCHEMA,
        "status_exact":config.get("status")==STATUS,
        "scope_exact":config.get("scope")==SCOPE,
        "candidate_pool_exact":tuple(config.get("candidate_pool") or ())==CANDIDATE_POOL,
        "selection_exact":(
            sel.get("target_replicates")==TARGET_REPLICATES
            and sel.get("candidate_order_is_frozen") is True
            and sel.get("event_selection")=="first natural reward at or after decision index 60"
            and sel.get("maximum_acquisition_decisions")==300
            and sel.get("sensory_sequence_window")=="source lags -60 through 0 inclusive"
            and tuple(sel.get("stable_context_volatile_keys_removed_recursively") or ())==(
                "survival_seconds","total_active_seconds","first_clear_seconds",
                "latest_clear_seconds","best_clear_seconds","seconds"
            )
            and sel.get("selection_is_outcome_blind") is True
            and sel.get("memory_expression_endpoints_must_not_be_computed_before_selection_freeze") is True
            and sel.get("no_seed_replacement_after_selection") is True
            and sel.get("fail_if_fewer_than_four_eligible_candidates") is True
        ),
        "conditions_exact":conds==EXPECTED_CONDITIONS and all(fields[k]==TARGET_FIELDS[k] for k in EXPECTED_CONDITIONS),
        "runtime_exact":(
            runtime.get("post_reward_delay_decisions")==POST_REWARD_DELAY_DECISIONS
            and runtime.get("boundary")=="after source lag -21 and before source lag -20"
            and runtime.get("primary_comparison_window")=="common terminal replay lags -20 through 0 inclusive"
            and runtime.get("recall_plasticity_frozen") is True
            and runtime.get("recall_external_reinforcement")=="none"
            and runtime.get("no_model_parameter_change") is True
        ),
        "replication_exact":(
            rep.get("candidate_condition")=="clear_vg_delay"
            and rep.get("reference_condition")=="intact"
            and rep.get("broad_reference")=="clear_broad_physical_transient"
            and tuple(rep.get("primary_neural_endpoints") or ())==(
                "mean_changed_kc_active_fraction",
                "mean_changed_l1_engaged_fraction",
                "mean_mbon07_state_difference_fraction",
            )
            and rep.get("replication_pattern")=="candidate condition is lower than intact on all three primary neural endpoints in each selected history"
            and rep.get("report_candidate_minus_intact") is True
            and rep.get("report_broad_minus_candidate") is True
            and rep.get("no_formal_significance_threshold") is True
        ),
        "claims_locked":set(claims)==CLAIM_KEYS and all(v is False for v in claims.values()),
    }

def _screen_candidates(*,base_checkpoint:Path,work_dir:Path):
    accepted=[]; screening=[]; seen_pre=set(); seen_sensory=set()
    for ordinal,seed in enumerate(CANDIDATE_POOL,1):
        cdir=work_dir/f"candidate-{ordinal:02d}-{seed}"
        cdir.mkdir(parents=True,exist_ok=True)
        try:
            trajectory,driver,event_index=_record_three_tau_trajectory(
                base_checkpoint=base_checkpoint,
                driver_checkpoint=cdir/"trajectory-driver.npz",
                trajectory_seed=seed,
            )
        except RuntimeError as exc:
            if "No qualifying natural reward" in str(exc):
                screening.append({"candidate_seed":seed,"accepted":False,"reason":"no_qualifying_reward"})
                continue
            raise
        pre_path=cdir/"pre-event.npz"
        pre=_build_pre_event_checkpoint(
            trajectory=trajectory,event_index=event_index,
            base_checkpoint=base_checkpoint,pre_event_checkpoint=pre_path,
        )
        sensory_rows=trajectory[event_index-FULL_HISTORY_DECISIONS:event_index+1]
        if len(sensory_rows)!=61:
            raise RuntimeError("Candidate sensory window mismatch")
        sensory=_sensory_digest(sensory_rows)
        pre_sha=pre["pre_event_checkpoint_sha256"]
        pre_unique=pre_sha not in seen_pre
        sensory_unique=sensory not in seen_sensory
        ok=pre_unique and sensory_unique
        row={
            "candidate_seed":seed,"event_index":event_index,
            "trajectory_digest":driver["trajectory_digest"],
            "pre_event_checkpoint_sha256":pre_sha,
            "stable_sensory_sequence_sha256":sensory,
            "pre_event_checkpoint_unique":pre_unique,
            "stable_sensory_sequence_unique":sensory_unique,
            "accepted":ok,
            "reason":"accepted" if ok else ("duplicate_pre_event_checkpoint" if not pre_unique else "duplicate_stable_sensory_sequence"),
        }
        screening.append(row)
        if not ok:
            continue
        seen_pre.add(pre_sha); seen_sensory.add(sensory)
        accepted.append({**row,"trajectory":trajectory,"pre_event_checkpoint":pre_path})
        if len(accepted)==TARGET_REPLICATES:
            break
    if len(accepted)!=TARGET_REPLICATES:
        raise RuntimeError(f"Neural-diversity gate found only {len(accepted)} eligible candidates")
    manifest={
        "schema":"neurofly-memory-vg-delay-replication-selection-v0.1",
        "candidate_pool":list(CANDIDATE_POOL),
        "selection_rule":"first four frozen-order candidates with unique pre-event checkpoint and stable sensory-sequence digests",
        "selected":[
            {
                "replicate_id":f"VR{i}","trajectory_seed":x["candidate_seed"],"event_index":x["event_index"],
                "trajectory_digest":x["trajectory_digest"],
                "pre_event_checkpoint_sha256":x["pre_event_checkpoint_sha256"],
                "stable_sensory_sequence_sha256":x["stable_sensory_sequence_sha256"],
            }
            for i,x in enumerate(accepted,1)
        ],
        "memory_expression_evaluated_before_manifest":False,
    }
    return accepted,screening,manifest

def _apply_clear(inner:Any,condition:str)->dict[str,Any]:
    fields=TARGET_FIELDS[condition]
    before=_plastic_edge_state(inner)["fraction_digest"]
    b=inner.brain
    changed=[]
    for field in fields:
        arr=getattr(b,field)
        initial=b.initial[field]
        import numpy as np
        if not np.array_equal(arr,initial):
            changed.append(field)
        arr[:] = initial
    after=_plastic_edge_state(inner)["fraction_digest"]
    if before!=after:
        raise RuntimeError("v/g-delay replication clear mutated synaptic memory")
    return {"condition":condition,"target_fields":list(fields),"changed_fields":changed,"memory_preserved":True}

def _run_condition(*,condition,pre_event_checkpoint,event,delay_rows,prefix_rows,terminal_rows,reward_pre,changed_mask,paired_delta):
    ni,n,ti,t=_build_memory_pair(pre_event_checkpoint=pre_event_checkpoint,event=event,delay_rows=delay_rows)
    _clear_for_recall(ni); _clear_for_recall(ti)
    nm=_plastic_edge_state(ni)["fraction_digest"]; tm=_plastic_edge_state(ti)["fraction_digest"]
    prefix=_replay_rows(
        none_inner=ni,true_inner=ti,rows=prefix_rows,start_lag=-60,
        reward_pre=reward_pre,changed_mask=changed_mask,paired_delta=paired_delta,
    )
    nb=_apply_clear(ni,condition); tb=_apply_clear(ti,condition)
    terminal_rows_out=_replay_rows(
        none_inner=ni,true_inner=ti,rows=terminal_rows,start_lag=-20,
        reward_pre=reward_pre,changed_mask=changed_mask,paired_delta=paired_delta,
    )
    terminal=_terminal_summary(terminal_rows_out)
    if nm!=_plastic_edge_state(ni)["fraction_digest"] or tm!=_plastic_edge_state(ti)["fraction_digest"]:
        raise RuntimeError("Frozen recall mutated synaptic memory")
    return {
        "condition":condition,"none_intervention":nb,"true_intervention":tb,
        "prefix_lags":[x["lag"] for x in prefix],"terminal":terminal,"memory_unchanged":True,
        "post_delay_fraction_digests":{"none":n["fraction_digest"],"true":t["fraction_digest"]},
    }

def _execute_selected(selected):
    import numpy as np
    reps=[]
    for i,item in enumerate(selected,1):
        trajectory=item["trajectory"]; event_index=item["event_index"]; pre_path=item["pre_event_checkpoint"]
        event=trajectory[event_index]
        prefix_rows=trajectory[event_index-60:event_index-20]
        terminal_rows=trajectory[event_index-20:event_index+1]
        delay_rows=trajectory[event_index+1:event_index+1+POST_REWARD_DELAY_DECISIONS]
        if len(prefix_rows)!=40 or len(terminal_rows)!=21 or len(delay_rows)!=5:
            raise RuntimeError("Selected replay geometry mismatch")
        _,rn,_,rt=_build_memory_pair(pre_event_checkpoint=pre_path,event=event,delay_rows=delay_rows)
        pre_inner=_restore_recentered(pre_path)
        c=pre_inner.brain.circuit
        reward_count=len(c["reward"])
        reward_mask=np.any(np.abs(c["gain"][:reward_count])>0.0,axis=0)
        reward_pre=np.asarray(c["pre"],dtype=np.int64)[reward_mask]
        delta=np.asarray(rt["post_delay_fraction"])[reward_mask]-np.asarray(rn["post_delay_fraction"])[reward_mask]
        changed=np.abs(delta)>CHANGED_TOLERANCE
        if not np.any(changed):
            raise RuntimeError("No changed reward edges")
        ref={"none":rn["fraction_digest"],"true":rt["fraction_digest"]}
        conditions={}
        for condition in EXPECTED_CONDITIONS:
            result=_run_condition(
                condition=condition,pre_event_checkpoint=pre_path,event=event,delay_rows=delay_rows,
                prefix_rows=prefix_rows,terminal_rows=terminal_rows,reward_pre=reward_pre,
                changed_mask=changed,paired_delta=delta,
            )
            if result["post_delay_fraction_digests"]!=ref:
                raise RuntimeError("Paired memory differs across conditions")
            conditions[condition]=result
        reps.append({
            "replicate_id":f"VR{i}","trajectory_seed":item["candidate_seed"],"event_index":event_index,
            "trajectory_digest":item["trajectory_digest"],
            "pre_event_checkpoint_sha256":item["pre_event_checkpoint_sha256"],
            "stable_sensory_sequence_sha256":item["stable_sensory_sequence_sha256"],
            "changed_reward_edge_count":int(changed.sum()),"conditions":conditions,
        })
    return reps

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
    intact=out["conditions"]["intact"]
    candidate=out["conditions"]["clear_vg_delay"]
    broad=out["conditions"]["clear_broad_physical_transient"]
    out["replication"]={
        "candidate_minus_intact":{m:round(candidate[m]-intact[m],12) for m in METRICS},
        "broad_minus_candidate":{m:round(broad[m]-candidate[m],12) for m in METRICS},
    }
    primary=(
        "mean_changed_kc_active_fraction",
        "mean_changed_l1_engaged_fraction",
        "mean_mbon07_state_difference_fraction",
    )
    per_replicate=[]
    for r in reps:
        row={"replicate_id":r["replicate_id"],"trajectory_seed":r["trajectory_seed"]}
        flags=[]
        for metric in primary:
            def metric_value(condition):
                rows=r["conditions"][condition]["terminal"]["per_lag"]
                if metric=="mean_changed_kc_active_fraction":
                    return mean(x["changed_presynaptic_kc_active_fraction"] for x in rows)
                if metric=="mean_changed_l1_engaged_fraction":
                    return mean(x["changed_reward_l1_engaged_fraction"] for x in rows)
                return mean(1.0 if x["any_mbon07_state_difference"] else 0.0 for x in rows)
            iv=metric_value("intact")
            cv=metric_value("clear_vg_delay")
            row[metric+"_intact"]=round(iv,12)
            row[metric+"_candidate"]=round(cv,12)
            row[metric+"_suppressed"]=cv < iv
            flags.append(cv < iv)
        row["all_three_primary_suppressed"]=all(flags)
        per_replicate.append(row)
    out["replication"]["per_replicate"]=per_replicate
    out["replication"]["replicates_with_all_three_primary_suppressed"]=sum(x["all_three_primary_suppressed"] for x in per_replicate)
    return out

def run_study(*,config_path:Path,base_checkpoint:Path,output_dir:Path,receipt_path:Path):
    config=json.loads(config_path.read_text()); cg=validate_config(config)
    if not all(cg.values()):
        raise ValueError("v/g-delay replication config failed validation")
    before=_sha256_file(base_checkpoint); output_dir.mkdir(parents=True,exist_ok=True)
    selected,screening,manifest=_screen_candidates(base_checkpoint=base_checkpoint,work_dir=output_dir/"screening")
    manifest["selection_sha256"]=_digest_json(manifest)
    manifest_path=output_dir/"selected-neural-histories.json"
    manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    manifest_file_sha=_sha256_file(manifest_path)
    reps=_execute_selected(selected)
    after=_sha256_file(base_checkpoint)
    pre=[r["pre_event_checkpoint_sha256"] for r in reps]; sensory=[r["stable_sensory_sequence_sha256"] for r in reps]
    eg={
        "source_checkpoint_unchanged":before==after,
        "selection_manifest_written_before_expression":manifest["memory_expression_evaluated_before_manifest"] is False,
        "four_replicates_selected":len(reps)==4,
        "four_unique_pre_event_checkpoints":len(set(pre))==4,
        "four_unique_stable_sensory_sequences":len(set(sensory))==4,
        "all_memory_frozen":all(r["conditions"][c]["memory_unchanged"] for r in reps for c in EXPECTED_CONDITIONS),
        "all_prefix_lags_exact":all(r["conditions"][c]["prefix_lags"]==list(range(-60,-20)) for r in reps for c in EXPECTED_CONDITIONS),
        "all_terminal_lags_exact":all(r["conditions"][c]["terminal"]["terminal_lags"]==list(range(-20,1)) for r in reps for c in EXPECTED_CONDITIONS),
        "claims_remain_locked":all(v is False for v in config["claim_policy"].values()),
    }
    valid=all(cg.values()) and all(eg.values())
    body={
        "schema":RECEIPT_SCHEMA,
        "status":"EXPLORATORY_MEMORY_VG_DELAY_REPLICATION_COMPLETE" if valid else "INVALID_EXECUTION",
        "scope":SCOPE,"execution_valid":valid,"config_gates":cg,"evidence_gates":eg,
        "source_checkpoint_sha256":before,"source_checkpoint_sha256_after":after,
        "screening":screening,"selection_manifest":manifest,
        "selection_manifest_file_sha256":manifest_file_sha,
        "replicates":reps,"aggregate":_aggregate(reps),
        "learning_validated":False,"temporal_cue_index_confirmed":False,
        "prefix_sequence_specificity_confirmed":False,"transient_state_carrier_confirmed":False,
        "memory_expression_causal":False,"replacement_confirmatory_authorized":False,
        "behavioral_promotion_authorized":False,"production_checkpoint_mutated":False,
        "human_science_review_required":True,
    }
    body["receipt_sha256"]=_digest_json(body)
    receipt_path.parent.mkdir(parents=True,exist_ok=True)
    tmp=receipt_path.with_suffix(receipt_path.suffix+".partial")
    tmp.write_text(json.dumps(body,indent=2,sort_keys=True)+"\n"); tmp.replace(receipt_path)
    return body

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="data/memory_vg_delay_replication_v01.json")
    p.add_argument("--base-checkpoint",required=True); p.add_argument("--output-dir",required=True); p.add_argument("--receipt",required=True)
    a=p.parse_args(argv)
    r=run_study(config_path=Path(a.config),base_checkpoint=Path(a.base_checkpoint),output_dir=Path(a.output_dir),receipt_path=Path(a.receipt))
    print(json.dumps({
        "schema":r["schema"],"status":r["status"],"execution_valid":r["execution_valid"],
        "selected":r["selection_manifest"]["selected"],"aggregate":r["aggregate"],"receipt_sha256":r["receipt_sha256"],
    },indent=2,sort_keys=True))
    return 0 if r["execution_valid"] else 1

if __name__=="__main__":
    raise SystemExit(main())
