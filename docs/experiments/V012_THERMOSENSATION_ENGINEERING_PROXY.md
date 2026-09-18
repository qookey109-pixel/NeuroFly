# V0.12 Thermosensation — Engineering Temperature-Change Proxy

## Goal

Add the first NeuroFly thermosensation sensory primitive without exposing an
absolute game/environment temperature directly to the neural agent.

Pipeline:

private ambient temperature history
→ temperature change
→ warming / cooling
→ thermal_change magnitude
→ receptor-domain payload

## Biological motivation

Adult Drosophila have opposing thermoreceptor populations associated with the
antenna and arista: warming excites warm cells and cooling excites cool cells.
Electrophysiological work also supports strongly phasic cooling responses in
aristal cold cells.

Sources used to motivate the direction-selective proxy:

- Frank et al., Nature (2015), Thermosensory processing in the Drosophila brain,
  PMCID PMC5488797.
- Budelli et al., Cell (2019), Ionotropic Receptors Specify the Morphogenesis
  of Phasic Sensors Controlling Rapid Thermal Preference in Drosophila,
  PMCID PMC6709853.

These sources motivate the sign of temperature change used by the proxy. They
do not calibrate this implementation's current amplitude, latency, temperature
scale, firing rate, synaptic weight or exact cell identity.

## Engineering encoding

Model: neurofly-thermal-change-proxy-v0.1

Encoding: virtual-ambient-temperature-change-only-proxy

For engineering temperature change dT and positive scale S:

- warming = clip(max(dT, 0) / S, 0, 1)
- cooling = clip(max(-dT, 0) / S, 0, 1)
- thermal_change = max(warming, cooling)

The default engineering scale is 1.0 degree C per unit receptor response. This
is an engineering normalization constant, not a biological threshold or
measured gain.

## Sensory-only boundary

The receptor payload never contains:

- absolute ambient temperature;
- previous absolute temperature;
- a target or preferred temperature;
- heat or cold source coordinates;
- goal direction;
- reward or aversive outcome;
- recommended action.

Only the bounded receptor-domain change channels are eligible for a future
neural-context integration.

## Stateful adapter

VirtualThermalSensor privately remembers the previous ambient temperature so it
can calculate the next temperature derivative.

The first observation after construction or reset is neutral because no
derivative exists yet.

Its persistence snapshot contains the private previous temperature solely for
restart continuity. That checkpoint object is control-plane state and is not a
neural payload.

## What this stage does not claim

This stage does not establish:

- exact adult thermoreceptor cell-type mapping;
- exact receptor molecular implementation;
- biological current or conductance;
- firing-rate calibration;
- response latency;
- preferred-temperature setpoint;
- noxious heat or cold nociception;
- behavioral thermotaxis;
- runtime neural stimulation authority.

## Runtime state

This PR intentionally stops before neural-context integration.

Current authority remains:

- neural_context_integration_authorized = false
- stimulation_current_authorized = false
- behavioral_promotion_authorized = false

A later stage may add a controlled virtual thermal environment and route only
these receptor channels into the same sensory firewall used by other modalities.
