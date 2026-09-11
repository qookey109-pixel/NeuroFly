# Third-party sources and attribution

NeuroFly is an independent project. It uses public research data and may optionally integrate third-party open-source implementations.

## Stonkfly

- Project: https://github.com/nftechie/stonkfly
- Initial reviewed pin: `78ef3e05ab0fa086032098558d893667068944a0`
- License: MIT
- Upstream copyright notice: Copyright (c) 2026 nftechie and DOOMFLY contributors

Stonkfly may be installed as an optional dependency. NeuroFly does not claim authorship of Stonkfly code. If Stonkfly code or substantial portions are later copied or adapted into this repository, the upstream MIT copyright and permission notice must remain with those portions.

Stonkfly itself documents that its connectome importer, inferred visual projection, spiking kernel and baseline-centered plasticity implementation are adapted from DOOMFLY under MIT terms.

## MaleCNS v1.0

- Project: https://male-cns.janelia.org/
- Data license reported by the upstream project: Creative Commons Attribution 4.0 (CC BY 4.0)

MaleCNS data should be downloaded separately rather than committed into NeuroFly's Git history. Experiments and publications using the dataset must preserve the required attribution and cite the associated release/paper as appropriate.

NeuroFly-generated processed artifacts must clearly distinguish upstream anatomical data from NeuroFly's modeled dynamics, adapters, inferred mappings, and experimental interpretations.

## Coinbase dependencies

Stonkfly optionally depends on Coinbase AgentKit and Coinbase Advanced Python SDK, both documented upstream as Apache-2.0 dependencies. NeuroFly's core does not require these packages. Money-moving integrations must remain optional and disabled by default.

## Scientific interpretation

A connectome supplies anatomical constraints. It does not by itself provide a complete physiological model, cognition, consciousness, pain, pleasure, or validated task competence. NeuroFly experiments must describe engineered sensory mappings, action decoders, reinforcement signals, and model assumptions explicitly.
