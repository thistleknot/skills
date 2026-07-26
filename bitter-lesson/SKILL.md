The RL-specific version of the test: does the hand-designed signal change what the optimal policy is, or does it change how fast you find it.

**Potential-based reward shaping** (Ng, Harada, Russell 1999). Add a shaping term shaped as the difference of a potential function; this is proven to leave the optimal policy unchanged, so it's a coordinate change on the reward landscape, not a verdict. Arbitrary hand-crafted reward bonuses that aren't potential-based can silently redefine the objective — that's the RL version of the evaluation-answer trap.

**Architecture as the representation prior, not the reward.** Bake symmetry/structure into the network instead of the reward: convolutions for spatial invariance, relative/egocentric coordinates instead of absolute, permutation-invariant layers for multi-agent. This is literally the halfKP move — recoordinate the input, leave the value function free to learn everything else.

**Auxiliary tasks feeding the shared encoder, not the policy head.** UNREAL-style auxiliary losses (pixel control, reward prediction, value replay) inject human-chosen prediction targets into representation learning, but the policy/value head still sits on top of a learned encoder that can outgrow them. The auxiliary signal accelerates representation learning without capping the final decision layer.

**Anneal the shaping term to zero.** Schedule the hand-crafted dense reward's coefficient to decay as training progresses, handing control back to sparse true reward once the agent has enough data to learn from it unassisted. This is the explicit crossover-retirement step — treat the feature as scaffolding with an expiration date.

**Learn the cumulants, not just the weights (successor features / general value functions).** Instead of hand-fixing what a feature means, specify what to predict (a cumulant) and let the network learn the representation and the weighting jointly. You're still injecting structure (what's worth tracking) but not the verdict (how much it matters).

**Prefer learned intrinsic reward (RND, ICM) over hand-formulated curiosity bonuses.** A self-supervised prediction-error signal is closer to a representation prior than a verdict, since it's derived from the model's own uncertainty rather than your judgment of what's interesting — and it should still be combined with, not substituted for, the true environment reward.

The recurring tell: linear value function over fixed hand features, or an un-annealed hand-crafted reward term, caps. Nonlinear approximator, potential-based shaping, or a decay schedule back to true reward — doesn't.