from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any


from .event_local_reinforcement_pulse import _build_pre_event_checkpoint, _restore_recentered
from .learning_control_study import _sha256_file
from .memory_history_expression_bridge import _build_memory_pair
from .memory_trace_reconstruction_audit import _record_three_tau_trajectory
from .memory_vg_delay_moderator_audit import (
    _extract_pre_intervention_features,
    _stable,
    _sensory_digest,
    _terminal_metrics,
)
from .memory_vg_delay_replication import _run_condition
from .smoke import _digest_json

CONFIG_SCHEMA="neurofly-memory-adaptation-moderator-validation-v0.1"
RECEIPT_SCHEMA="neurofly-memory-adaptation-moderator-validation-receipt-v0.1"
STATUS="PREREGISTERED_EXPLORATORY_VALIDATION"
SCOPE="real-malecns-reward-memory-adaptation-moderator-validation"
FULL_HISTORY_DECISIONS=60
POST_REWARD_DELAY_DECISIONS=5
CHANGED_TOLERANCE=1e-12
TARGET_PER_STRATUM=4
QUIESCENT_MAX=0.10
ENGAGED_MIN=0.50
LEAD_FEATURE="adaptation.paired_mean.std"
CANDIDATE_POOL=(
    5903,5909,5923,5927,5939,5953,5981,5987,6007,6011,6029,6037,
    6043,6047,6053,6067,6073,6079,6089,6091,6101,6113,6121,6131,
    6133,6143,6151,6163,6173,6197,6203,6211,6221,6229,6247,6257,
    6263,6271,6287,6299,6301,6311,6323,6329,6337,6343,6353,6361,
)
EXPECTED_CONDITIONS=("intact","clear_vg_delay")
TARGET_FIELDS={
    "intact":(),
    "clear_vg_delay":("v","g","refractory","queue","queue_count"),
}
PRIMARY_ENDPOINTS=(
    "mean_changed_kc_active_fraction",
    "mean_changed_l1_engaged_fraction",
    "mean_mbon07_state_difference_fraction",
)
CLAIM_KEYS={
    "learning_validated","temporal_cue_index_confirmed","prefix_sequence_specificity_confirmed",
    "transient_state_carrier_confirmed","memory_expression_causal","moderator_confirmed",
    "replacement_confirmatory_authorized","behavioral_promotion_authorized",
}

def validate_config(config:dict[str,Any])->dict[str,bool]:
    sel=config.get("selection") or {}
    mod=config.get("moderator") or {}
    runtime=config.get("runtime") or {}
    effect=config.get("effect_label") or {}
    val=config.get("validation") or {}
    claims=config.get("claim_policy") or {}
    conds=tuple(x.get("id") for x in runtime.get("conditions",[]) if isinstance(x,dict))
    fields={x.get("id"):tuple(x.get("target_fields") or ()) for x in runtime.get("conditions",[]) if isinstance(x,dict)}
    return {
        "schema_exact":config.get("schema")==CONFIG_SCHEMA,
        "status_exact":config.get("status")==STATUS,
        "scope_exact":config.get("scope")==SCOPE,
        "candidate_pool_exact":tuple(config.get("candidate_pool") or ())==CANDIDATE_POOL,
        "selection_exact":(
            sel.get("target_engaged")==TARGET_PER_STRATUM
            and sel.get("target_quiescent")==TARGET_PER_STRATUM
            and sel.get("candidate_order_is_frozen") is True
            and sel.get("event_selection")=="first natural reward at or after decision index 60"
            and sel.get("maximum_acquisition_decisions")==300
            and sel.get("unique_pre_event_checkpoint_required") is True
            and sel.get("unique_stable_sensory_sequence_required") is True
            and sel.get("selection_is_effect_outcome_blind") is True
            and sel.get("no_seed_replacement_after_selection") is True
            and sel.get("fail_if_either_stratum_has_fewer_than_four_histories") is True
        ),
        "moderator_exact":(
            mod.get("feature")==LEAD_FEATURE
            and mod.get("timing")=="after exact prefix lag -21 and before boundary intervention"
            and float(mod.get("quiescent_max"))==QUIESCENT_MAX
            and float(mod.get("engaged_min"))==ENGAGED_MIN
            and mod.get("intermediate_policy")=="record and skip from target strata"
            and mod.get("thresholds_are_discovery_derived_and_frozen_before_new_effect_outcomes") is True
        ),
        "runtime_exact":(
            runtime.get("post_reward_delay_decisions")==POST_REWARD_DELAY_DECISIONS
            and runtime.get("boundary")=="after source lag -21 and before source lag -20"
            and runtime.get("recall_plasticity_frozen") is True
            and runtime.get("recall_external_reinforcement")=="none"
            and runtime.get("no_model_parameter_change") is True
            and conds==EXPECTED_CONDITIONS
            and all(fields[k]==TARGET_FIELDS[k] for k in EXPECTED_CONDITIONS)
        ),
        "effect_exact":(
            tuple(effect.get("primary_endpoints") or ())==PRIMARY_ENDPOINTS
            and effect.get("suppression")=="clear_vg_delay is lower than intact on all three primary endpoints"
            and effect.get("reversal")=="clear_vg_delay is higher than intact on all three primary endpoints"
            and effect.get("mixed")=="all other endpoint-sign patterns"
        ),
        "validation_exact":(
            val.get("primary_directional_target")=="engaged suppression count is greater than quiescent suppression count"
            and val.get("secondary_directional_target")=="engaged mean candidate-minus-intact delta is more negative than quiescent mean delta on all three primary endpoints"
            and val.get("prefix_crosscheck")=="report whether lag -21 changed-KC and changed-edge expression are jointly nonzero within each adaptation stratum"
            and val.get("no_significance_threshold") is True
            and val.get("passing_both_targets_supports_replication_not_confirmation") is True
        ),
        "claims_locked":set(claims)==CLAIM_KEYS and all(v is False for v in claims.values()),
    }

def _classify(value:float)->str:
    if value<=QUIESCENT_MAX:
        return "quiescent"
    if value>=ENGAGED_MIN:
        return "engaged"
    return "intermediate"

def _candidate_pre_effect(*,base_checkpoint:Path,work_dir:Path,seed:int,ordinal:int):
    import numpy as np
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
            return None,{"candidate_seed":seed,"accepted":False,"reason":"no_qualifying_reward"}
        raise
    if event_index<FULL_HISTORY_DECISIONS:
        return None,{"candidate_seed":seed,"accepted":False,"reason":"insufficient_history","event_index":event_index}

    pre_path=cdir/"pre-event.npz"
    pre=_build_pre_event_checkpoint(
        trajectory=trajectory,event_index=event_index,
        base_checkpoint=base_checkpoint,pre_event_checkpoint=pre_path,
    )
    sensory_rows=trajectory[event_index-FULL_HISTORY_DECISIONS:event_index+1]
    if len(sensory_rows)!=61:
        raise RuntimeError("Candidate sensory window mismatch")
    sensory=_sensory_digest(sensory_rows)

    event=trajectory[event_index]
    prefix_rows=trajectory[event_index-60:event_index-20]
    terminal_rows=trajectory[event_index-20:event_index+1]
    delay_rows=trajectory[event_index+1:event_index+1+POST_REWARD_DELAY_DECISIONS]
    if len(prefix_rows)!=40 or len(terminal_rows)!=21 or len(delay_rows)!=POST_REWARD_DELAY_DECISIONS:
        raise RuntimeError("Candidate replay geometry mismatch")

    _,rn,_,rt=_build_memory_pair(pre_event_checkpoint=pre_path,event=event,delay_rows=delay_rows)
    pre_inner=_restore_recentered(pre_path); c=pre_inner.brain.circuit
    reward_count=len(c["reward"])
    reward_mask=np.any(np.abs(c["gain"][:reward_count])>0.0,axis=0)
    reward_pre=np.asarray(c["pre"],dtype=np.int64)[reward_mask]
    delta=np.asarray(rt["post_delay_fraction"])[reward_mask]-np.asarray(rn["post_delay_fraction"])[reward_mask]
    changed=np.abs(delta)>CHANGED_TOLERANCE
    if not np.any(changed):
        raise RuntimeError("No changed reward edges")
    changed_count=int(changed.sum())

    features=_extract_pre_intervention_features(
        pre_event_checkpoint=pre_path,event=event,delay_rows=delay_rows,prefix_rows=prefix_rows,
        reward_pre=reward_pre,changed_mask=changed,paired_delta=delta,
        event_index=event_index,changed_edge_count=changed_count,
    )
    lead=float(features[LEAD_FEATURE])
    stratum=_classify(lead)
    prefix_joint_nonzero=(
        float(features["prefix.lag_minus_21_changed_kc_active_fraction"])>0.0
        and float(features["prefix.lag_minus_21_changed_l1_engaged_fraction"])>0.0
    )
    prepared={
        "trajectory_seed":seed,"event_index":event_index,"trajectory_digest":driver["trajectory_digest"],
        "pre_event_checkpoint_sha256":pre["pre_event_checkpoint_sha256"],
        "stable_sensory_sequence_sha256":sensory,
        "pre_event_checkpoint":pre_path,"event":event,"delay_rows":delay_rows,
        "prefix_rows":prefix_rows,"terminal_rows":terminal_rows,"reward_pre":reward_pre,
        "changed_mask":changed,"paired_delta":delta,"changed_reward_edge_count":changed_count,
        "reference_fraction_digests":{"none":rn["fraction_digest"],"true":rt["fraction_digest"]},
        "lead_feature_value":lead,"stratum":stratum,
        "prefix_joint_nonzero":prefix_joint_nonzero,
        "prefix_lag_minus_21_changed_kc_active_fraction":features["prefix.lag_minus_21_changed_kc_active_fraction"],
        "prefix_lag_minus_21_changed_l1_engaged_fraction":features["prefix.lag_minus_21_changed_l1_engaged_fraction"],
    }
    screening={
        "candidate_seed":seed,"event_index":event_index,
        "pre_event_checkpoint_sha256":pre["pre_event_checkpoint_sha256"],
        "stable_sensory_sequence_sha256":sensory,
        "moderator_feature":LEAD_FEATURE,"moderator_value":lead,"stratum":stratum,
        "effect_endpoints_evaluated":False,
    }
    return prepared,screening

def _select_stratified(*,base_checkpoint:Path,work_dir:Path):
    selected={"engaged":[],"quiescent":[]}
    screening=[]; seen_pre=set(); seen_sensory=set()
    for ordinal,seed in enumerate(CANDIDATE_POOL,1):
        item,row=_candidate_pre_effect(base_checkpoint=base_checkpoint,work_dir=work_dir,seed=seed,ordinal=ordinal)
        screening.append(row)
        if item is None:
            continue
        pre=item["pre_event_checkpoint_sha256"]; sensory=item["stable_sensory_sequence_sha256"]
        if pre in seen_pre:
            row["accepted"]=False; row["reason"]="duplicate_pre_event_checkpoint"; continue
        if sensory in seen_sensory:
            row["accepted"]=False; row["reason"]="duplicate_stable_sensory_sequence"; continue
        if item["stratum"]=="intermediate":
            row["accepted"]=False; row["reason"]="intermediate_stratum"; continue
        if len(selected[item["stratum"]])>=TARGET_PER_STRATUM:
            row["accepted"]=False; row["reason"]="stratum_already_full"; continue

        seen_pre.add(pre); seen_sensory.add(sensory)
        selected[item["stratum"]].append(item)
        row["accepted"]=True; row["reason"]="accepted"
        if all(len(selected[s])==TARGET_PER_STRATUM for s in ("engaged","quiescent")):
            break

    if any(len(selected[s])!=TARGET_PER_STRATUM for s in ("engaged","quiescent")):
        raise RuntimeError(
            f"Stratified gate incomplete: engaged={len(selected['engaged'])} quiescent={len(selected['quiescent'])}"
        )

    ordered=selected["engaged"]+selected["quiescent"]
    manifest={
        "schema":"neurofly-memory-adaptation-moderator-stratified-selection-v0.1",
        "moderator_feature":LEAD_FEATURE,
        "quiescent_max":QUIESCENT_MAX,
        "engaged_min":ENGAGED_MIN,
        "effect_endpoints_evaluated_before_manifest":False,
        "selected":[
            {
                "replicate_id":f"AV{i}",
                "trajectory_seed":x["trajectory_seed"],"event_index":x["event_index"],
                "trajectory_digest":x["trajectory_digest"],
                "pre_event_checkpoint_sha256":x["pre_event_checkpoint_sha256"],
                "stable_sensory_sequence_sha256":x["stable_sensory_sequence_sha256"],
                "stratum":x["stratum"],"moderator_value":x["lead_feature_value"],
                "prefix_joint_nonzero":x["prefix_joint_nonzero"],
                "prefix_lag_minus_21_changed_kc_active_fraction":x["prefix_lag_minus_21_changed_kc_active_fraction"],
                "prefix_lag_minus_21_changed_l1_engaged_fraction":x["prefix_lag_minus_21_changed_l1_engaged_fraction"],
            }
            for i,x in enumerate(ordered,1)
        ],
    }
    manifest["selection_sha256"]=_digest_json(manifest)
    return ordered,screening,manifest

def _execute_effects(selected:list[dict[str,Any]]):
    reps=[]
    for i,item in enumerate(selected,1):
        conditions={}
        for condition in EXPECTED_CONDITIONS:
            result=_run_condition(
                condition=condition,pre_event_checkpoint=item["pre_event_checkpoint"],event=item["event"],
                delay_rows=item["delay_rows"],prefix_rows=item["prefix_rows"],terminal_rows=item["terminal_rows"],
                reward_pre=item["reward_pre"],changed_mask=item["changed_mask"],paired_delta=item["paired_delta"],
            )
            if result["post_delay_fraction_digests"]!=item["reference_fraction_digests"]:
                raise RuntimeError("Paired memory differs across conditions")
            conditions[condition]=result
        intact=_terminal_metrics(conditions["intact"]["terminal"])
        candidate=_terminal_metrics(conditions["clear_vg_delay"]["terminal"])
        deltas={k:round(candidate[k]-intact[k],12) for k in PRIMARY_ENDPOINTS}
        lower=all(deltas[k]<0 for k in PRIMARY_ENDPOINTS)
        higher=all(deltas[k]>0 for k in PRIMARY_ENDPOINTS)
        label="suppression" if lower else ("reversal" if higher else "mixed")
        reps.append({
            "replicate_id":f"AV{i}","trajectory_seed":item["trajectory_seed"],
            "event_index":item["event_index"],"stratum":item["stratum"],
            "moderator_value":item["lead_feature_value"],
            "prefix_joint_nonzero":item["prefix_joint_nonzero"],
            "effect_label":label,"primary_endpoint_deltas":deltas,
            "changed_reward_edge_count":item["changed_reward_edge_count"],
            "pre_event_checkpoint_sha256":item["pre_event_checkpoint_sha256"],
            "stable_sensory_sequence_sha256":item["stable_sensory_sequence_sha256"],
            "conditions":conditions,
        })
    return reps

def _validate_effect(reps:list[dict[str,Any]])->dict[str,Any]:
    by={s:[r for r in reps if r["stratum"]==s] for s in ("engaged","quiescent")}
    suppression_counts={s:sum(r["effect_label"]=="suppression" for r in rows) for s,rows in by.items()}
    mean_deltas={}
    for s,rows in by.items():
        mean_deltas[s]={k:round(mean(float(r["primary_endpoint_deltas"][k]) for r in rows),12) for k in PRIMARY_ENDPOINTS}
    primary=suppression_counts["engaged"]>suppression_counts["quiescent"]
    secondary=all(mean_deltas["engaged"][k]<mean_deltas["quiescent"][k] for k in PRIMARY_ENDPOINTS)
    return {
        "suppression_counts":suppression_counts,
        "effect_label_counts":{
            s:{label:sum(r["effect_label"]==label for r in rows) for label in ("suppression","reversal","mixed")}
            for s,rows in by.items()
        },
        "mean_candidate_minus_intact_deltas":mean_deltas,
        "primary_directional_target_passed":primary,
        "secondary_directional_target_passed":secondary,
        "adaptation_moderator_replication_supported":primary and secondary,
        "moderator_confirmed":False,
        "prefix_crosscheck":{
            s:{
                "joint_nonzero_count":sum(bool(r["prefix_joint_nonzero"]) for r in rows),
                "n":len(rows),
            }
            for s,rows in by.items()
        },
    }

def run_study(*,config_path:Path,base_checkpoint:Path,output_dir:Path,receipt_path:Path):
    config=json.loads(config_path.read_text()); cg=validate_config(config)
    if not all(cg.values()):
        raise ValueError("Adaptation moderator validation config failed validation")
    before=_sha256_file(base_checkpoint); output_dir.mkdir(parents=True,exist_ok=True)

    selected,screening,manifest=_select_stratified(base_checkpoint=base_checkpoint,work_dir=output_dir/"screening")
    manifest_path=output_dir/"stratified-selection.json"
    manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    manifest_file_sha=_sha256_file(manifest_path)

    reps=_execute_effects(selected)
    after=_sha256_file(base_checkpoint)
    validation=_validate_effect(reps)
    pre=[r["pre_event_checkpoint_sha256"] for r in reps]
    sensory=[r["stable_sensory_sequence_sha256"] for r in reps]
    eg={
        "source_checkpoint_unchanged":before==after,
        "stratified_manifest_written_before_effects":manifest["effect_endpoints_evaluated_before_manifest"] is False,
        "four_engaged_selected":sum(x["stratum"]=="engaged" for x in manifest["selected"])==4,
        "four_quiescent_selected":sum(x["stratum"]=="quiescent" for x in manifest["selected"])==4,
        "eight_unique_pre_event_checkpoints":len(set(pre))==8,
        "eight_unique_stable_sensory_sequences":len(set(sensory))==8,
        "all_memory_frozen":all(r["conditions"][c]["memory_unchanged"] for r in reps for c in EXPECTED_CONDITIONS),
        "all_prefix_lags_exact":all(r["conditions"][c]["prefix_lags"]==list(range(-60,-20)) for r in reps for c in EXPECTED_CONDITIONS),
        "all_terminal_lags_exact":all(r["conditions"][c]["terminal"]["terminal_lags"]==list(range(-20,1)) for r in reps for c in EXPECTED_CONDITIONS),
        "claims_remain_locked":all(v is False for v in config["claim_policy"].values()),
    }
    valid=all(cg.values()) and all(eg.values())
    body={
        "schema":RECEIPT_SCHEMA,
        "status":"EXPLORATORY_ADAPTATION_MODERATOR_VALIDATION_COMPLETE" if valid else "INVALID_EXECUTION",
        "scope":SCOPE,"execution_valid":valid,"config_gates":cg,"evidence_gates":eg,
        "source_checkpoint_sha256":before,"source_checkpoint_sha256_after":after,
        "screening":screening,"stratified_selection_manifest":manifest,
        "stratified_selection_manifest_file_sha256":manifest_file_sha,
        "replicates":reps,"validation":validation,
        "learning_validated":False,"temporal_cue_index_confirmed":False,
        "prefix_sequence_specificity_confirmed":False,"transient_state_carrier_confirmed":False,
        "memory_expression_causal":False,"moderator_confirmed":False,
        "replacement_confirmatory_authorized":False,"behavioral_promotion_authorized":False,
        "production_checkpoint_mutated":False,"human_science_review_required":True,
    }
    body["receipt_sha256"]=_digest_json(body)
    receipt_path.parent.mkdir(parents=True,exist_ok=True)
    tmp=receipt_path.with_suffix(receipt_path.suffix+".partial")
    tmp.write_text(json.dumps(body,indent=2,sort_keys=True)+"\n"); tmp.replace(receipt_path)
    return body

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="data/memory_adaptation_moderator_validation_v01.json")
    p.add_argument("--base-checkpoint",required=True)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--receipt",required=True)
    a=p.parse_args(argv)
    r=run_study(config_path=Path(a.config),base_checkpoint=Path(a.base_checkpoint),output_dir=Path(a.output_dir),receipt_path=Path(a.receipt))
    print(json.dumps({
        "schema":r["schema"],"status":r["status"],"execution_valid":r["execution_valid"],
        "selected":r["stratified_selection_manifest"]["selected"],
        "validation":r["validation"],"receipt_sha256":r["receipt_sha256"],
    },indent=2,sort_keys=True))
    return 0 if r["execution_valid"] else 1

if __name__=="__main__":
    raise SystemExit(main())
