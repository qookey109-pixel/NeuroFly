from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from .compartment_plasticity_diagnostic import _plastic_edge_state
from .event_local_reinforcement_pulse import _build_pre_event_checkpoint, _restore_recentered
from .learning_control_study import _sha256_file
from .memory_history_expression_bridge import _build_memory_pair
from .memory_physical_state_interaction import (
    EXPECTED_CONDITIONS,
    _aggregate,
    _run_condition,
)
from .memory_trace_reconstruction_audit import _record_three_tau_trajectory
from .smoke import _digest_json

CONFIG_SCHEMA="neurofly-memory-interaction-diversity-recovery-v0.1"
RECEIPT_SCHEMA="neurofly-memory-interaction-diversity-recovery-receipt-v0.1"
STATUS="PREREGISTERED_EXPLORATORY_EXECUTION"
SCOPE="real-malecns-reward-memory-physical-state-interaction-diversity-recovery"
TARGET_REPLICATES=4
FULL_HISTORY_DECISIONS=60
POST_REWARD_DELAY_DECISIONS=5
CHANGED_TOLERANCE=1e-12
CANDIDATE_POOL=(5003,5009,5011,5021,5023,5039,5051,5059,5077,5081,5087,5099,5101,5107,5113,5119,5147,5153,5167,5171)
VOLATILE_CONTEXT_KEYS={"survival_seconds","total_active_seconds","first_clear_seconds","latest_clear_seconds","best_clear_seconds","seconds"}
CLAIM_KEYS={"learning_validated","temporal_cue_index_confirmed","prefix_sequence_specificity_confirmed","transient_state_carrier_confirmed","memory_expression_causal","replacement_confirmatory_authorized","behavioral_promotion_authorized"}

def _stable(value:Any)->Any:
    if isinstance(value,dict):
        return {str(k):_stable(v) for k,v in sorted(value.items(),key=lambda kv:str(kv[0])) if str(k) not in VOLATILE_CONTEXT_KEYS}
    if isinstance(value,list):
        return [_stable(x) for x in value]
    if isinstance(value,tuple):
        return [_stable(x) for x in value]
    return value

def _sensory_digest(rows:list[dict[str,Any]])->str:
    payload=[]
    for row in rows:
        payload.append({
            "frame_sha256":hashlib.sha256(row["frame"].tobytes()).hexdigest(),
            "stable_context_sha256":_digest_json(_stable(row["context"])),
        })
    return _digest_json(payload)

def validate_config(config:dict[str,Any])->dict[str,bool]:
    sel=config.get("selection") or {}
    runtime=config.get("runtime") or {}
    ia=config.get("interaction_analysis") or {}
    claims=config.get("claim_policy") or {}
    conditions=tuple(x.get("id") for x in runtime.get("conditions",[]) if isinstance(x,dict))
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
        "runtime_exact":(
            runtime.get("post_reward_delay_decisions")==POST_REWARD_DELAY_DECISIONS
            and runtime.get("boundary")=="after source lag -21 and before source lag -20"
            and runtime.get("primary_comparison_window")=="common terminal replay lags -20 through 0 inclusive"
            and runtime.get("recall_plasticity_frozen") is True
            and runtime.get("recall_external_reinforcement")=="none"
            and runtime.get("no_model_parameter_change") is True
            and conditions==EXPECTED_CONDITIONS
        ),
        "interaction_exact":(
            ia.get("subsystem_a")=="clear_vg_adaptation"
            and ia.get("subsystem_b")=="clear_input_delay"
            and ia.get("combined")=="clear_broad_physical_transient"
            and ia.get("descriptive_interaction_contrast")=="combined - subsystem_a - subsystem_b + intact"
            and ia.get("no_formal_significance_threshold") is True
        ),
        "claims_locked":set(claims)==CLAIM_KEYS and all(v is False for v in claims.values()),
    }

def _screen_candidates(*,base_checkpoint:Path,work_dir:Path)->tuple[list[dict[str,Any]],list[dict[str,Any]],dict[str,Any]]:
    accepted=[]
    screening=[]
    seen_pre=set()
    seen_sensory=set()
    for ordinal,seed in enumerate(CANDIDATE_POOL,1):
        candidate_dir=work_dir/f"candidate-{ordinal:02d}-{seed}"
        candidate_dir.mkdir(parents=True,exist_ok=True)
        try:
            trajectory,driver,event_index=_record_three_tau_trajectory(
                base_checkpoint=base_checkpoint,
                driver_checkpoint=candidate_dir/"trajectory-driver.npz",
                trajectory_seed=seed,
            )
        except RuntimeError as exc:
            if "No qualifying natural reward" in str(exc):
                screening.append({"candidate_seed":seed,"accepted":False,"reason":"no_qualifying_reward"})
                continue
            raise
        if event_index<FULL_HISTORY_DECISIONS:
            screening.append({"candidate_seed":seed,"accepted":False,"reason":"insufficient_history","event_index":event_index})
            continue
        pre_path=candidate_dir/"pre-event.npz"
        pre=_build_pre_event_checkpoint(
            trajectory=trajectory,event_index=event_index,
            base_checkpoint=base_checkpoint,pre_event_checkpoint=pre_path,
        )
        sensory_rows=trajectory[event_index-FULL_HISTORY_DECISIONS:event_index+1]
        if len(sensory_rows)!=FULL_HISTORY_DECISIONS+1:
            raise RuntimeError("Candidate sensory window mismatch")
        sensory=_sensory_digest(sensory_rows)
        pre_sha=pre["pre_event_checkpoint_sha256"]
        pre_unique=pre_sha not in seen_pre
        sensory_unique=sensory not in seen_sensory
        is_accepted=pre_unique and sensory_unique
        row={
            "candidate_seed":seed,
            "event_index":event_index,
            "trajectory_digest":driver["trajectory_digest"],
            "pre_event_checkpoint_sha256":pre_sha,
            "stable_sensory_sequence_sha256":sensory,
            "pre_event_checkpoint_unique":pre_unique,
            "stable_sensory_sequence_unique":sensory_unique,
            "accepted":is_accepted,
            "reason":"accepted" if is_accepted else (
                "duplicate_pre_event_checkpoint" if not pre_unique else "duplicate_stable_sensory_sequence"
            ),
        }
        screening.append(row)
        if not is_accepted:
            continue
        seen_pre.add(pre_sha); seen_sensory.add(sensory)
        accepted.append({
            **row,
            "trajectory":trajectory,
            "driver":driver,
            "pre_event_checkpoint":pre_path,
        })
        if len(accepted)==TARGET_REPLICATES:
            break
    if len(accepted)!=TARGET_REPLICATES:
        raise RuntimeError(f"Neural-diversity gate found only {len(accepted)} eligible candidates")
    manifest={
        "schema":"neurofly-memory-interaction-diversity-selection-v0.1",
        "selection_rule":"first four frozen-order candidates with unique pre-event checkpoint and stable sensory-sequence digests",
        "candidate_pool":list(CANDIDATE_POOL),
        "selected":[
            {
                "replicate_id":f"DR{i}",
                "trajectory_seed":x["candidate_seed"],
                "event_index":x["event_index"],
                "trajectory_digest":x["trajectory_digest"],
                "pre_event_checkpoint_sha256":x["pre_event_checkpoint_sha256"],
                "stable_sensory_sequence_sha256":x["stable_sensory_sequence_sha256"],
            }
            for i,x in enumerate(accepted,1)
        ],
        "memory_expression_evaluated_before_manifest":False,
    }
    return accepted,screening,manifest

def _execute_selected(*,selected:list[dict[str,Any]])->list[dict[str,Any]]:
    import numpy as np
    reps=[]
    for i,item in enumerate(selected,1):
        trajectory=item["trajectory"]; event_index=item["event_index"]; pre_path=item["pre_event_checkpoint"]
        event=trajectory[event_index]
        prefix_rows=trajectory[event_index-60:event_index-20]
        terminal_rows=trajectory[event_index-20:event_index+1]
        delay_rows=trajectory[event_index+1:event_index+1+POST_REWARD_DELAY_DECISIONS]
        if len(prefix_rows)!=40 or len(terminal_rows)!=21 or len(delay_rows)!=POST_REWARD_DELAY_DECISIONS:
            raise RuntimeError("Selected replay geometry mismatch")
        _,rn,_,rt=_build_memory_pair(pre_event_checkpoint=pre_path,event=event,delay_rows=delay_rows)
        pre_inner=_restore_recentered(pre_path)
        c=pre_inner.brain.circuit
        reward_count=len(c["reward"])
        reward_mask=np.any(np.abs(c["gain"][:reward_count])>0.0,axis=0)
        reward_pre=np.asarray(c["pre"],dtype=np.int64)[reward_mask]
        paired_delta=np.asarray(rt["post_delay_fraction"])[reward_mask]-np.asarray(rn["post_delay_fraction"])[reward_mask]
        changed=np.abs(paired_delta)>CHANGED_TOLERANCE
        if not np.any(changed):
            raise RuntimeError("No changed reward edges for selected history")
        ref={"none":rn["fraction_digest"],"true":rt["fraction_digest"]}
        conditions={}
        for condition in EXPECTED_CONDITIONS:
            result=_run_condition(
                condition=condition,pre_event_checkpoint=pre_path,event=event,delay_rows=delay_rows,
                prefix_rows=prefix_rows,terminal_rows=terminal_rows,reward_pre=reward_pre,
                changed_mask=changed,paired_delta=paired_delta,
            )
            if result["post_delay_fraction_digests"]!=ref:
                raise RuntimeError("Paired memory differs across conditions")
            conditions[condition]=result
        reps.append({
            "replicate_id":f"DR{i}",
            "trajectory_seed":item["candidate_seed"],
            "event_index":event_index,
            "trajectory_digest":item["trajectory_digest"],
            "pre_event_checkpoint_sha256":item["pre_event_checkpoint_sha256"],
            "stable_sensory_sequence_sha256":item["stable_sensory_sequence_sha256"],
            "changed_reward_edge_count":int(changed.sum()),
            "conditions":conditions,
        })
    return reps

def run_study(*,config_path:Path,base_checkpoint:Path,output_dir:Path,receipt_path:Path)->dict[str,Any]:
    config=json.loads(config_path.read_text())
    cg=validate_config(config)
    if not all(cg.values()):
        raise ValueError("Diversity-recovery config failed validation")
    source_before=_sha256_file(base_checkpoint)
    output_dir.mkdir(parents=True,exist_ok=True)
    selected,screening,manifest=_screen_candidates(base_checkpoint=base_checkpoint,work_dir=output_dir/"screening")
    manifest_path=output_dir/"selected-neural-histories.json"
    manifest["selection_sha256"]=_digest_json(manifest)
    manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    manifest_sha=_sha256_file(manifest_path)

    reps=_execute_selected(selected=selected)
    source_after=_sha256_file(base_checkpoint)
    pre_digests=[r["pre_event_checkpoint_sha256"] for r in reps]
    sensory_digests=[r["stable_sensory_sequence_sha256"] for r in reps]
    eg={
        "source_checkpoint_unchanged":source_before==source_after,
        "selection_manifest_written_before_expression":manifest["memory_expression_evaluated_before_manifest"] is False,
        "four_replicates_selected":len(reps)==TARGET_REPLICATES,
        "four_unique_pre_event_checkpoints":len(set(pre_digests))==TARGET_REPLICATES,
        "four_unique_stable_sensory_sequences":len(set(sensory_digests))==TARGET_REPLICATES,
        "all_memory_frozen":all(r["conditions"][c]["memory_unchanged"] for r in reps for c in EXPECTED_CONDITIONS),
        "all_prefix_lags_exact":all(r["conditions"][c]["prefix_lags"]==list(range(-60,-20)) for r in reps for c in EXPECTED_CONDITIONS),
        "all_terminal_lags_exact":all(r["conditions"][c]["terminal"]["terminal_lags"]==list(range(-20,1)) for r in reps for c in EXPECTED_CONDITIONS),
        "scheduler_physical_state_preserved":all(
            r["conditions"]["coherent_scheduler_rebuild"]["none_intervention"]["physical_state_preserved"]
            and r["conditions"]["coherent_scheduler_rebuild"]["true_intervention"]["physical_state_preserved"]
            for r in reps
        ),
        "claims_remain_locked":all(v is False for v in config["claim_policy"].values()),
    }
    valid=all(cg.values()) and all(eg.values())
    body={
        "schema":RECEIPT_SCHEMA,
        "status":"EXPLORATORY_MEMORY_INTERACTION_DIVERSITY_RECOVERY_COMPLETE" if valid else "INVALID_EXECUTION",
        "scope":SCOPE,
        "execution_valid":valid,
        "config_gates":cg,
        "evidence_gates":eg,
        "source_checkpoint_sha256":source_before,
        "source_checkpoint_sha256_after":source_after,
        "screening":screening,
        "selection_manifest":manifest,
        "selection_manifest_file_sha256":manifest_sha,
        "replicates":reps,
        "aggregate":_aggregate(reps),
        "learning_validated":False,
        "temporal_cue_index_confirmed":False,
        "prefix_sequence_specificity_confirmed":False,
        "transient_state_carrier_confirmed":False,
        "memory_expression_causal":False,
        "replacement_confirmatory_authorized":False,
        "behavioral_promotion_authorized":False,
        "production_checkpoint_mutated":False,
        "human_science_review_required":True,
    }
    body["receipt_sha256"]=_digest_json(body)
    receipt_path.parent.mkdir(parents=True,exist_ok=True)
    tmp=receipt_path.with_suffix(receipt_path.suffix+".partial")
    tmp.write_text(json.dumps(body,indent=2,sort_keys=True)+"\n")
    tmp.replace(receipt_path)
    return body

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="data/memory_interaction_diversity_recovery_v01.json")
    p.add_argument("--base-checkpoint",required=True)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--receipt",required=True)
    a=p.parse_args(argv)
    r=run_study(config_path=Path(a.config),base_checkpoint=Path(a.base_checkpoint),output_dir=Path(a.output_dir),receipt_path=Path(a.receipt))
    print(json.dumps({
        "schema":r["schema"],"status":r["status"],"execution_valid":r["execution_valid"],
        "selected":r["selection_manifest"]["selected"],"aggregate":r["aggregate"],
        "receipt_sha256":r["receipt_sha256"],
    },indent=2,sort_keys=True))
    return 0 if r["execution_valid"] else 1

if __name__=="__main__":
    raise SystemExit(main())
