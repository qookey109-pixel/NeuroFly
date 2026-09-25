from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any

from .compartment_plasticity_diagnostic import _plastic_edge_state
from .event_local_reinforcement_pulse import _build_pre_event_checkpoint, _restore_recentered
from .learning_control_study import _sha256_file
from .memory_history_expression_bridge import _build_memory_pair, _clear_for_recall
from .memory_physical_state_interaction import _replay_rows
from .memory_trace_reconstruction_audit import _record_three_tau_trajectory
from .memory_vg_delay_replication import _run_condition
from .smoke import _digest_json

CONFIG_SCHEMA="neurofly-memory-vg-delay-moderator-audit-v0.1"
RECEIPT_SCHEMA="neurofly-memory-vg-delay-moderator-audit-receipt-v0.1"
STATUS="PREREGISTERED_EXPLORATORY_DISCOVERY"
SCOPE="real-malecns-reward-memory-vg-delay-history-moderator-audit"
TARGET_REPLICATES=8
FULL_HISTORY_DECISIONS=60
POST_REWARD_DELAY_DECISIONS=5
CHANGED_TOLERANCE=1e-12
CANDIDATE_POOL=(5603,5609,5623,5639,5641,5647,5651,5653,5657,5659,5669,5683,5689,5693,5701,5711,5717,5737,5741,5743,5749,5779,5783,5791,5801,5807,5813,5821,5827,5839)
VOLATILE_CONTEXT_KEYS={"survival_seconds","total_active_seconds","first_clear_seconds","latest_clear_seconds","best_clear_seconds","seconds"}
EXPECTED_CONDITIONS=("intact","clear_vg_delay")
TARGET_FIELDS={
    "intact":(),
    "clear_vg_delay":("v","g","refractory","queue","queue_count"),
}
PHYSICAL_FIELDS=("v","g","adaptation","luminance","refractory","queue_count","nactive")
PHYSICAL_STATS=("mean","std","p95_abs","max_abs","nonzero_fraction")
PRIMARY_ENDPOINTS=(
    "mean_changed_kc_active_fraction",
    "mean_changed_l1_engaged_fraction",
    "mean_mbon07_state_difference_fraction",
)
CLAIM_KEYS={"learning_validated","temporal_cue_index_confirmed","prefix_sequence_specificity_confirmed","transient_state_carrier_confirmed","memory_expression_causal","moderator_confirmed","replacement_confirmatory_authorized","behavioral_promotion_authorized"}

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
    mf=config.get("moderator_features") or {}
    el=config.get("effect_label") or {}
    ap=config.get("analysis_policy") or {}
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
            and sel.get("moderator_features_must_not_be_labeled_by_effect_before_selection_freeze") is True
            and sel.get("no_seed_replacement_after_selection") is True
            and sel.get("fail_if_fewer_than_eight_eligible_candidates") is True
        ),
        "runtime_exact":(
            runtime.get("post_reward_delay_decisions")==POST_REWARD_DELAY_DECISIONS
            and runtime.get("boundary")=="after source lag -21 and before source lag -20"
            and runtime.get("primary_comparison_window")=="common terminal replay lags -20 through 0 inclusive"
            and runtime.get("recall_plasticity_frozen") is True
            and runtime.get("recall_external_reinforcement")=="none"
            and runtime.get("no_model_parameter_change") is True
            and conds==EXPECTED_CONDITIONS
            and all(fields[k]==TARGET_FIELDS[k] for k in EXPECTED_CONDITIONS)
        ),
        "features_exact":(
            mf.get("timing")=="measured after exact prefix lag -21 and before boundary intervention"
            and tuple(mf.get("physical_fields") or ())==PHYSICAL_FIELDS
            and tuple(mf.get("physical_summary_statistics") or ())==PHYSICAL_STATS
            and tuple(mf.get("trajectory_features") or ())==("event_index","changed_reward_edge_count")
            and mf.get("all_feature_names_and_formulas_are_frozen_before_effect_labeling") is True
        ),
        "effect_label_exact":(
            tuple(el.get("primary_endpoints") or ())==PRIMARY_ENDPOINTS
            and el.get("suppression")=="clear_vg_delay is lower than intact on all three primary endpoints"
            and el.get("reversal")=="clear_vg_delay is higher than intact on all three primary endpoints"
            and el.get("mixed")=="all other endpoint-sign patterns"
        ),
        "analysis_policy_exact":(
            ap.get("exploratory_discovery_only") is True
            and ap.get("report_all_frozen_features") is True
            and ap.get("report_group_means_by_effect_label_when_group_size_is_nonzero") is True
            and ap.get("report_standardized_mean_difference_for_suppression_vs_non_suppression_when_both_groups_exist") is True
            and ap.get("no_feature_selection_threshold") is True
            and ap.get("no_significance_claim") is True
            and ap.get("no_causal_claim") is True
            and ap.get("any_moderator_hypothesis_requires_new_preregistered_cohort") is True
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
        if event_index<FULL_HISTORY_DECISIONS:
            screening.append({"candidate_seed":seed,"accepted":False,"reason":"insufficient_history","event_index":event_index})
            continue
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
        "schema":"neurofly-memory-vg-delay-moderator-selection-v0.1",
        "candidate_pool":list(CANDIDATE_POOL),
        "selection_rule":"first eight frozen-order candidates with unique pre-event checkpoint and stable sensory-sequence digests",
        "selected":[
            {
                "replicate_id":f"MA{i}","trajectory_seed":x["candidate_seed"],"event_index":x["event_index"],
                "trajectory_digest":x["trajectory_digest"],
                "pre_event_checkpoint_sha256":x["pre_event_checkpoint_sha256"],
                "stable_sensory_sequence_sha256":x["stable_sensory_sequence_sha256"],
            }
            for i,x in enumerate(accepted,1)
        ],
        "effect_endpoints_evaluated_before_manifest":False,
    }
    return accepted,screening,manifest

def _stats(value:Any)->dict[str,float]:
    import numpy as np
    a=np.asarray(value,dtype=np.float64).reshape(-1)
    if a.size==0:
        return {k:0.0 for k in PHYSICAL_STATS}
    abs_a=np.abs(a)
    return {
        "mean":round(float(a.mean()),12),
        "std":round(float(a.std()),12),
        "p95_abs":round(float(np.quantile(abs_a,0.95)),12),
        "max_abs":round(float(abs_a.max()),12),
        "nonzero_fraction":round(float(np.count_nonzero(abs_a>1e-12)/a.size),12),
    }

def _flatten_physical(none_inner:Any,true_inner:Any)->dict[str,float]:
    features={}
    for field in PHYSICAL_FIELDS:
        ns=_stats(getattr(none_inner.brain,field))
        ts=_stats(getattr(true_inner.brain,field))
        for stat in PHYSICAL_STATS:
            nv=ns[stat]; tv=ts[stat]
            features[f"{field}.none.{stat}"]=nv
            features[f"{field}.true.{stat}"]=tv
            features[f"{field}.paired_mean.{stat}"]=round((nv+tv)/2.0,12)
            features[f"{field}.absolute_branch_difference.{stat}"]=round(abs(tv-nv),12)
    return features

def _prefix_features(rows:list[dict[str,Any]])->dict[str,float]:
    last=rows[-1]
    return {
        "prefix.mean_changed_kc_active_fraction":round(mean(x["changed_presynaptic_kc_active_fraction"] for x in rows),12),
        "prefix.mean_changed_l1_engaged_fraction":round(mean(x["changed_reward_l1_engaged_fraction"] for x in rows),12),
        "prefix.mbon07_state_difference_fraction":round(mean(1.0 if x["any_mbon07_state_difference"] else 0.0 for x in rows),12),
        "prefix.mbon07_spike_difference_fraction":round(mean(1.0 if x["mbon07_total_spike_delta"]!=0 else 0.0 for x in rows),12),
        "prefix.action_divergence_fraction":round(mean(1.0 if x["action_diverged"] else 0.0 for x in rows),12),
        "prefix.lag_minus_21_changed_kc_active_fraction":last["changed_presynaptic_kc_active_fraction"],
        "prefix.lag_minus_21_changed_l1_engaged_fraction":last["changed_reward_l1_engaged_fraction"],
        "prefix.lag_minus_21_mbon07_state_difference":1.0 if last["any_mbon07_state_difference"] else 0.0,
        "prefix.lag_minus_21_mbon07_spike_difference":1.0 if last["mbon07_total_spike_delta"]!=0 else 0.0,
    }

def _extract_pre_intervention_features(*,pre_event_checkpoint:Path,event:dict[str,Any],delay_rows:list[dict[str,Any]],prefix_rows:list[dict[str,Any]],reward_pre:Any,changed_mask:Any,paired_delta:Any,event_index:int,changed_edge_count:int)->dict[str,float]:
    ni,_,ti,_=_build_memory_pair(pre_event_checkpoint=pre_event_checkpoint,event=event,delay_rows=delay_rows)
    _clear_for_recall(ni); _clear_for_recall(ti)
    rows=_replay_rows(
        none_inner=ni,true_inner=ti,rows=prefix_rows,start_lag=-60,
        reward_pre=reward_pre,changed_mask=changed_mask,paired_delta=paired_delta,
    )
    features={
        "trajectory.event_index":float(event_index),
        "trajectory.changed_reward_edge_count":float(changed_edge_count),
    }
    features.update(_prefix_features(rows))
    features.update(_flatten_physical(ni,ti))
    return features

def _prepare_selected(*,selected:list[dict[str,Any]],output_dir:Path):
    import numpy as np
    prepared=[]; feature_rows=[]
    for i,item in enumerate(selected,1):
        trajectory=item["trajectory"]; event_index=item["event_index"]; pre_path=item["pre_event_checkpoint"]
        event=trajectory[event_index]
        prefix_rows=trajectory[event_index-60:event_index-20]
        terminal_rows=trajectory[event_index-20:event_index+1]
        delay_rows=trajectory[event_index+1:event_index+1+POST_REWARD_DELAY_DECISIONS]
        if len(prefix_rows)!=40 or len(terminal_rows)!=21 or len(delay_rows)!=POST_REWARD_DELAY_DECISIONS:
            raise RuntimeError("Selected replay geometry mismatch")
        _,rn,_,rt=_build_memory_pair(pre_event_checkpoint=pre_path,event=event,delay_rows=delay_rows)
        pre_inner=_restore_recentered(pre_path); c=pre_inner.brain.circuit
        reward_count=len(c["reward"]); reward_mask=np.any(np.abs(c["gain"][:reward_count])>0.0,axis=0)
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
        feature_rows.append({
            "replicate_id":f"MA{i}",
            "trajectory_seed":item["candidate_seed"],
            "event_index":event_index,
            "pre_event_checkpoint_sha256":item["pre_event_checkpoint_sha256"],
            "stable_sensory_sequence_sha256":item["stable_sensory_sequence_sha256"],
            "features":features,
        })
        prepared.append({
            "replicate_id":f"MA{i}","trajectory_seed":item["candidate_seed"],"event_index":event_index,
            "trajectory_digest":item["trajectory_digest"],
            "pre_event_checkpoint_sha256":item["pre_event_checkpoint_sha256"],
            "stable_sensory_sequence_sha256":item["stable_sensory_sequence_sha256"],
            "event":event,"pre_event_checkpoint":pre_path,"delay_rows":delay_rows,
            "prefix_rows":prefix_rows,"terminal_rows":terminal_rows,
            "reward_pre":reward_pre,"changed_mask":changed,"paired_delta":delta,
            "changed_reward_edge_count":changed_count,"features":features,
            "reference_fraction_digests":{"none":rn["fraction_digest"],"true":rt["fraction_digest"]},
        })
    manifest={
        "schema":"neurofly-memory-vg-delay-pre-intervention-features-v0.1",
        "timing":"after exact prefix lag -21 and before any boundary intervention",
        "effect_endpoints_evaluated_before_manifest":False,
        "rows":feature_rows,
    }
    manifest["feature_manifest_sha256"]=_digest_json(manifest)
    path=output_dir/"pre-intervention-features.json"
    path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return prepared,manifest,_sha256_file(path)

def _terminal_metrics(terminal:dict[str,Any])->dict[str,float]:
    rows=terminal["per_lag"]
    return {
        "mean_changed_kc_active_fraction":mean(x["changed_presynaptic_kc_active_fraction"] for x in rows),
        "mean_changed_l1_engaged_fraction":mean(x["changed_reward_l1_engaged_fraction"] for x in rows),
        "mean_mbon07_state_difference_fraction":mean(1.0 if x["any_mbon07_state_difference"] else 0.0 for x in rows),
    }

def _execute_effects(prepared:list[dict[str,Any]]):
    reps=[]
    for item in prepared:
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
            "replicate_id":item["replicate_id"],"trajectory_seed":item["trajectory_seed"],
            "event_index":item["event_index"],"trajectory_digest":item["trajectory_digest"],
            "pre_event_checkpoint_sha256":item["pre_event_checkpoint_sha256"],
            "stable_sensory_sequence_sha256":item["stable_sensory_sequence_sha256"],
            "changed_reward_edge_count":item["changed_reward_edge_count"],
            "pre_intervention_features":item["features"],
            "effect_label":label,"primary_endpoint_deltas":deltas,
            "conditions":conditions,
        })
    return reps

def _condition_aggregate(reps,condition):
    terminals=[r["conditions"][condition]["terminal"] for r in reps]
    vals=[]
    for t in terminals:
        vals.append(_terminal_metrics(t))
    return {k:round(mean(v[k] for v in vals),12) for k in PRIMARY_ENDPOINTS}

def _population_std(values:list[float])->float:
    if not values:
        return 0.0
    m=mean(values)
    return math.sqrt(mean((x-m)**2 for x in values))

def _moderator_analysis(reps):
    labels={"suppression":0,"reversal":0,"mixed":0}
    for r in reps:
        labels[r["effect_label"]]+=1
    feature_names=sorted(reps[0]["pre_intervention_features"])
    groups={
        "suppression":[r for r in reps if r["effect_label"]=="suppression"],
        "reversal":[r for r in reps if r["effect_label"]=="reversal"],
        "mixed":[r for r in reps if r["effect_label"]=="mixed"],
        "non_suppression":[r for r in reps if r["effect_label"]!="suppression"],
    }
    all_features={}
    for feature in feature_names:
        entry={}
        for gname,rows in groups.items():
            if rows:
                values=[float(r["pre_intervention_features"][feature]) for r in rows]
                entry[gname+"_n"]=len(values)
                entry[gname+"_mean"]=round(mean(values),12)
                entry[gname+"_std"]=round(_population_std(values),12)
        s=groups["suppression"]; n=groups["non_suppression"]
        if s and n:
            sv=[float(r["pre_intervention_features"][feature]) for r in s]
            nv=[float(r["pre_intervention_features"][feature]) for r in n]
            pooled=math.sqrt((_population_std(sv)**2+_population_std(nv)**2)/2.0)
            entry["suppression_minus_non_suppression_mean"]=round(mean(sv)-mean(nv),12)
            entry["standardized_mean_difference"]=None if pooled<=1e-15 else round((mean(sv)-mean(nv))/pooled,12)
        all_features[feature]=entry
    return {
        "label_counts":labels,
        "feature_count":len(feature_names),
        "all_frozen_features":all_features,
        "feature_ranking_or_threshold_applied":False,
        "exploratory_only":True,
    }

def run_study(*,config_path:Path,base_checkpoint:Path,output_dir:Path,receipt_path:Path):
    config=json.loads(config_path.read_text()); cg=validate_config(config)
    if not all(cg.values()):
        raise ValueError("v/g-delay moderator audit config failed validation")
    before=_sha256_file(base_checkpoint); output_dir.mkdir(parents=True,exist_ok=True)
    selected,screening,selection_manifest=_screen_candidates(base_checkpoint=base_checkpoint,work_dir=output_dir/"screening")
    selection_manifest["selection_sha256"]=_digest_json(selection_manifest)
    selection_path=output_dir/"selected-neural-histories.json"
    selection_path.write_text(json.dumps(selection_manifest,indent=2,sort_keys=True)+"\n")
    selection_file_sha=_sha256_file(selection_path)

    prepared,feature_manifest,feature_manifest_file_sha=_prepare_selected(selected=selected,output_dir=output_dir)
    reps=_execute_effects(prepared)
    after=_sha256_file(base_checkpoint)
    pre=[r["pre_event_checkpoint_sha256"] for r in reps]; sensory=[r["stable_sensory_sequence_sha256"] for r in reps]
    eg={
        "source_checkpoint_unchanged":before==after,
        "selection_manifest_written_before_effects":selection_manifest["effect_endpoints_evaluated_before_manifest"] is False,
        "pre_intervention_features_written_before_effects":feature_manifest["effect_endpoints_evaluated_before_manifest"] is False,
        "eight_replicates_selected":len(reps)==TARGET_REPLICATES,
        "eight_unique_pre_event_checkpoints":len(set(pre))==TARGET_REPLICATES,
        "eight_unique_stable_sensory_sequences":len(set(sensory))==TARGET_REPLICATES,
        "all_memory_frozen":all(r["conditions"][c]["memory_unchanged"] for r in reps for c in EXPECTED_CONDITIONS),
        "all_prefix_lags_exact":all(r["conditions"][c]["prefix_lags"]==list(range(-60,-20)) for r in reps for c in EXPECTED_CONDITIONS),
        "all_terminal_lags_exact":all(r["conditions"][c]["terminal"]["terminal_lags"]==list(range(-20,1)) for r in reps for c in EXPECTED_CONDITIONS),
        "claims_remain_locked":all(v is False for v in config["claim_policy"].values()),
    }
    valid=all(cg.values()) and all(eg.values())
    body={
        "schema":RECEIPT_SCHEMA,
        "status":"EXPLORATORY_MEMORY_VG_DELAY_MODERATOR_AUDIT_COMPLETE" if valid else "INVALID_EXECUTION",
        "scope":SCOPE,"execution_valid":valid,"config_gates":cg,"evidence_gates":eg,
        "source_checkpoint_sha256":before,"source_checkpoint_sha256_after":after,
        "screening":screening,"selection_manifest":selection_manifest,
        "selection_manifest_file_sha256":selection_file_sha,
        "pre_intervention_feature_manifest":feature_manifest,
        "pre_intervention_feature_manifest_file_sha256":feature_manifest_file_sha,
        "replicates":reps,
        "aggregate":{
            "intact":_condition_aggregate(reps,"intact"),
            "clear_vg_delay":_condition_aggregate(reps,"clear_vg_delay"),
            "moderator_analysis":_moderator_analysis(reps),
        },
        "learning_validated":False,"temporal_cue_index_confirmed":False,
        "prefix_sequence_specificity_confirmed":False,"transient_state_carrier_confirmed":False,
        "memory_expression_causal":False,"moderator_confirmed":False,
        "replacement_confirmatory_authorized":False,"behavioral_promotion_authorized":False,
        "production_checkpoint_mutated":False,"human_science_review_required":True,
    }
    body["receipt_sha256"]=_digest_json(body)
    tmp=receipt_path.with_suffix(receipt_path.suffix+".partial")
    receipt_path.parent.mkdir(parents=True,exist_ok=True)
    tmp.write_text(json.dumps(body,indent=2,sort_keys=True)+"\n"); tmp.replace(receipt_path)
    return body

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="data/memory_vg_delay_moderator_audit_v01.json")
    p.add_argument("--base-checkpoint",required=True)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--receipt",required=True)
    a=p.parse_args(argv)
    r=run_study(config_path=Path(a.config),base_checkpoint=Path(a.base_checkpoint),output_dir=Path(a.output_dir),receipt_path=Path(a.receipt))
    print(json.dumps({
        "schema":r["schema"],"status":r["status"],"execution_valid":r["execution_valid"],
        "selected":r["selection_manifest"]["selected"],
        "label_counts":r["aggregate"]["moderator_analysis"]["label_counts"],
        "receipt_sha256":r["receipt_sha256"],
    },indent=2,sort_keys=True))
    return 0 if r["execution_valid"] else 1

if __name__=="__main__":
    raise SystemExit(main())
