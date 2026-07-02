---
title: "Composable RL Wrapper Building Blocks"
author: "Boeing Conversational AI"
version: "1.0"
description: "Generalized wrapper layer for composing RL training environments from reusable interface adapters"
---

***definitions***

- :DynamicSystem: is the underlying simulator or state-transition mechanism before RL-facing adaptation.
- :BaseEnvironment: is a task environment that exposes state transition and reward behavior but is not yet standardized for downstream RL tooling.
- :Wrapper: is a component that transforms another :DynamicSystem:, :BaseEnvironment:, or :Wrapper: into a new RL-facing interface.
- :ComposableWrapper: is a :Wrapper: designed to be stacked with other wrappers without redefining unrelated concerns.
- :ObservationWrapper: is a :ComposableWrapper: that transforms the exposed observation while preserving task dynamics.
- :ActionWrapper: is a :ComposableWrapper: that transforms agent actions before they reach the wrapped system.
- :RewardWrapper: is a :ComposableWrapper: that transforms or computes reward without redefining observation or transition logic.
- :TerminationWrapper: is a :ComposableWrapper: that defines or overrides episode termination logic.
- :TruncationWrapper: is a :ComposableWrapper: that enforces budget-based stopping such as max steps.
- :FeatureWrapper: is an :ObservationWrapper: that converts raw state into a feature representation for learning.
- :IndexWrapper: is an :ObservationWrapper: that maps structured finite state into a flat integer index.
- :DiscretizationWrapper: is an :ObservationWrapper: that converts continuous state into coarse categorical bins.
- :GymWrapper: is a :ComposableWrapper: that exposes Gymnasium-style `reset()` and `step()` semantics.
- :MonitoringWrapper: is a :ComposableWrapper: that records episode statistics or diagnostic metadata while preserving task dynamics and control semantics.
- :RecordingWrapper: is a :ComposableWrapper: that captures rendered rollouts or videos for inspection without changing task behavior.
- :VectorizationAdapter: is an adapter that exposes multiple environment instances through one batched training interface.
- :EnvironmentFactory: is a reusable constructor that creates configured environment instances without embedding training logic.
- :TrainingCallback: is a reusable training-time observer that reads progress, metrics, or events without changing environment semantics.
- :EvaluationCallback: is a reusable training-time controller that triggers separate evaluation rollouts without changing the training environment contract.
- :StateMapper: is a reusable mapping between structured state and encoded observation.
- :ActionMapper: is a reusable mapping between agent action indices and underlying control actions.
- :RewardEvaluator: is a reusable policy for computing reward from state or transition information.
- :EpisodeState: is the wrapper-maintained runtime status such as current step count, done flag, or cached observation.
- :InfoPayload: is the auxiliary metadata returned alongside observations and rewards.
- :TrainingEnvironment: is the final composed wrapper stack consumed by an RL algorithm.
- :WrapperStack: is an ordered composition of wrappers over one underlying system.
- :InterfaceContract: is the required behavior at a wrapper boundary.
- :ObservationSpaceDescriptor: is the declared shape or type of the observation exposed by a wrapper.
- :ActionSpaceDescriptor: is the declared shape or type of the action interface exposed by a wrapper.
- :FiniteStructuredState: is a state representation with a finite enumerated identity, such as coordinates, modes, or tuples that can be losslessly indexed.
- :ContinuousPhysicalState: is a state representation with real-valued variables such as position, velocity, angle, or force-related quantities.
- :TabularObservation: is a discrete observation encoding suitable for lookup-based RL methods.
- :FeatureObservation: is a fixed-length numeric representation suitable for approximation-based learners.
- :TaskSemantics: is the domain-specific meaning of reward, success, failure, and natural episode ending.
- :InfrastructureLayer: is a non-task wrapper or adapter such as monitoring, recording, vectorization, or evaluation scheduling that preserves task semantics.

***implementation reqs***

- The wrapper library should keep observation transformation, action transformation, reward computation, termination logic, truncation logic, and API standardization as separate responsibilities.
- A :ComposableWrapper: should wrap exactly one lower layer and should delegate unchanged responsibilities rather than reimplement them.
- A :WrapperStack: should allow the same :DynamicSystem: to be exposed through multiple task formulations by swapping wrappers rather than editing the underlying system.
- A :GymWrapper: should be the final adapter layer when downstream training code expects Gymnasium-style interfaces.
- A :StateMapper:, :ActionMapper:, and :RewardEvaluator: should be reusable helper objects or helper modules rather than hidden one-off logic when the same mapping pattern appears across wrappers.
- Wrapper names should reflect responsibility rather than environment-specific detail when the behavior is general.
- The library should preserve environment-specific wrappers only where task semantics are genuinely domain-specific.
- The library should support both finite structured state and continuous physical state.
- The library should support both raw-state observations and engineered-feature observations.
- The library should support natural terminal states and external truncation budgets as distinct concepts.
- The library should allow wrappers to pass through `info` metadata from lower layers while adding wrapper-specific metadata.
- The library should not force reward shaping, discretization, or feature extraction into every stack.
- The library should keep the base environment usable without Gymnasium when direct pedagogical or debugging access is helpful.
- The library should allow optional infrastructure layers for monitoring, recording, and vectorized execution without collapsing those concerns into task-definition wrappers.
- The library should support separate environment construction and evaluation orchestration through :EnvironmentFactory:, :TrainingCallback:, and :EvaluationCallback: roles when experiments require them.
- The library should classify reusable patterns by state topology, action topology, observation encoding, and task semantics rather than by benchmark-specific environment names.

***functional specs***

- :WrapperLibrary: should define reusable wrapper roles that can be composed independently.

  ***acceptance tests***

  - Observation transformation is specified independently from action transformation.
  - Reward logic is specified independently from observation encoding.
  - Termination logic is specified independently from truncation logic.

- :WrapperLibrary: should support a minimal wrapper stack for finite-state tabular RL.

  ***acceptance tests***

  - A :BaseEnvironment: can be wrapped by an :IndexWrapper: and then a :GymWrapper:.
  - The resulting :TrainingEnvironment: exposes discrete observations suitable for tabular RL.
  - The wrapper stack does not require feature extraction when the state is already finite and structured.

- :WrapperLibrary: should support a minimal wrapper stack for continuous-state control with engineered features.

  ***acceptance tests***

  - A :DynamicSystem: can be wrapped by a task-level reward and termination layer, then by a :FeatureWrapper:, then by a :GymWrapper:.
  - The resulting :TrainingEnvironment: exposes fixed-length feature vectors suitable for function approximation.
  - The wrapper stack can include an :ActionMapper: when agent actions differ from lower-layer control values.

- :ObservationWrapper: should transform observations without redefining the lower-layer transition mechanism.

  ***acceptance tests***

  - The wrapper reads lower-layer state or observation.
  - The wrapper emits a transformed observation.
  - The wrapper delegates action application and transition dynamics unchanged unless paired with another wrapper.

- :ActionWrapper: should transform agent-facing actions into lower-layer actions without redefining observation encoding.

  ***acceptance tests***

  - The wrapper accepts an agent action in the outer action space.
  - The wrapper maps that action into the wrapped action space.
  - The wrapper delegates transition execution after mapping.

- :RewardWrapper: should compute or modify reward without changing observation identity unless explicitly composed with another wrapper.

  ***acceptance tests***

  - Reward can be computed from resulting state, transition, or domain-specific evaluation logic.
  - The wrapper preserves the lower-layer observation path unless another wrapper changes it.

- :TerminationWrapper: should determine whether an episode has ended because of task-defined success or failure.

  ***acceptance tests***

  - Terminal success and terminal failure are represented as natural episode endings.
  - Terminal logic is separable from max-step truncation.

- :TruncationWrapper: should enforce episode budgets without redefining task success or failure.

  ***acceptance tests***

  - The wrapper increments an internal step counter.
  - The wrapper emits truncation when the configured budget is exhausted.
  - The wrapper does not relabel a natural terminal event as truncation.

- :GymWrapper: should expose a standardized RL training interface.

  ***acceptance tests***

  - `reset()` returns observation and info.
  - `step(action)` returns observation, reward, terminated, truncated, and info.
  - Observation and action space descriptors are available when required by downstream tooling.

- :MonitoringWrapper: should attach episode statistics or diagnostics without changing task semantics.

  ***acceptance tests***

  - The wrapper preserves observation, action, reward, termination, and truncation behavior of the lower layer.
  - The wrapper adds monitoring metadata or tracked statistics through `info`, logs, or wrapper-owned state.
  - The wrapper can be inserted or removed without changing task-definition logic.

- :RecordingWrapper: should capture rendered episodes for debugging or reporting without changing the training task.

  ***acceptance tests***

  - The wrapper preserves lower-layer transition, reward, and termination behavior.
  - The wrapper records rollout frames or videos using explicit output configuration.
  - The wrapper can be applied to a separate evaluation environment without modifying the training environment.

- :VectorizationAdapter: should expose multiple environment instances through a batched interface for downstream training code.

  ***acceptance tests***

  - Multiple lower-layer environments can be stepped through one outer interface.
  - The adapter preserves each member environment's task semantics.
  - The adapter exposes batched observations and accepts batched or per-environment actions according to its declared contract.

- :EnvironmentFactory: should construct configured environments without embedding algorithm logic.

  ***acceptance tests***

  - The same factory pattern can create multiple seeded instances of one environment.
  - Construction concerns remain separate from training loops and policy code.
  - The produced environment can be wrapped further by monitoring, recording, vectorization, or task-specific wrappers.

- :TrainingCallback: should observe or log training progress without redefining environment behavior.

  ***acceptance tests***

  - A callback can read step counts, episodic metrics, or model-side logs.
  - A callback can accumulate experiment history for plotting or analysis.
  - Removing the callback does not change the environment interface or task semantics.

- :EvaluationCallback: should trigger periodic evaluation rollouts without redefining the training environment interface.

  ***acceptance tests***

  - The callback can run policy evaluation on a separate environment instance.
  - Evaluation scheduling is explicit configuration rather than hidden control flow.
  - Removing the callback does not change the training environment contract.

- :IndexWrapper: should map structured finite state into a stable integer encoding.

  ***acceptance tests***

  - A 2D coordinate-like state can be mapped to one discrete state index.
  - The mapping is deterministic and reversible when the underlying state space is finite and enumerated.
  - The wrapper preserves the semantic identity of the original state.

- :DiscretizationWrapper: should convert selected continuous variables into categorical bins.

  ***acceptance tests***

  - Continuous observations can be reduced to coarse discrete observations.
  - Bin thresholds are explicit configuration rather than hidden constants.
  - The wrapper can ignore dimensions that are intentionally excluded from the reduced observation.

- :FeatureWrapper: should convert raw physical or structured state into a fixed-length feature vector.

  ***acceptance tests***

  - The feature representation is deterministic for a given lower-layer state.
  - The exposed observation dimension is fixed and declared.
  - Feature extraction can coexist with separate action mapping and termination logic.

- :WrapperLibrary: should preserve the distinction between raw system state and agent-facing observation.

  ***acceptance tests***

  - A wrapper may expose a transformed observation while the wrapped layer retains a richer complete state.
  - The library documentation names this distinction explicitly.

- :WrapperLibrary: should preserve the distinction between base environment and wrapper stack.

  ***acceptance tests***

  - The same :BaseEnvironment: can appear in more than one :WrapperStack:.
  - One wrapper stack can target tabular methods.
  - Another wrapper stack can target approximation-based methods.

- :WrapperLibrary: should support generalized environment-composition patterns already present in the provided materials.

  ***acceptance tests***

  - A finite-state coordinate task can be represented as :IndexWrapper: plus :GymWrapper:.
  - A task-defined control environment over raw dynamics can be represented as :RewardWrapper: plus :TerminationWrapper: over :DynamicSystem:.
  - A feature-based training adapter can be represented as :ActionWrapper:, :FeatureWrapper:, :TruncationWrapper:, and :GymWrapper:.
  - A library-supplied continuous-control task can be composed with optional :VectorizationAdapter:, optional :MonitoringWrapper:, and optional evaluation-only :RecordingWrapper:.
  - Periodic experiment logging is representable through :TrainingCallback: without changing the environment interface.
  - Periodic evaluation playback is representable through :EvaluationCallback: over a separate evaluation environment.

- :FiniteStateTabularPattern: should be described as a wrapper composition for lookup-based training.

  ***acceptance tests***

  - The lower layer is a :BaseEnvironment: with finite structured state.
  - An :IndexWrapper: maps structured state into a :TabularObservation:.
  - A :GymWrapper: exposes the training API.
  - An optional :TruncationWrapper: adds max-step stopping.

- :ContinuousControlPattern: should be described as a wrapper composition for learning over real-valued dynamics.

  ***acceptance tests***

  - The lower layer is a :DynamicSystem: or continuous-state :BaseEnvironment:.
  - A task-level wrapper computes reward and terminal status from lower-layer state or transition results.
  - An optional :DiscretizationWrapper: exposes simplified categorical observations for toy policies.
  - An optional :FeatureWrapper: exposes engineered vectors for function approximation.
  - An optional :ActionWrapper: maps agent actions into lower-layer control values.
  - A :GymWrapper: exposes the final training interface.

- :VectorizedTrainingPattern: should be described as an infrastructure composition for parallel rollout collection.

  ***acceptance tests***

  - A base training environment or wrapper stack can be replicated across multiple instances.
  - A :VectorizationAdapter: exposes batched stepping and reset behavior.
  - An optional :MonitoringWrapper: records per-episode statistics across the vectorized setup.
  - Task semantics remain owned by the lower environment stack rather than by the vectorization layer.

- :EvaluationRecordingPattern: should be described as a separate evaluation composition for inspection and reporting.

  ***acceptance tests***

  - An evaluation environment can be created separately from the training environment.
  - A :RecordingWrapper: can wrap the evaluation environment without changing training-time behavior.
  - An :EvaluationCallback: can trigger playback or recording on an explicit schedule.
  - Training and evaluation concerns remain separable.

- :WrapperDocstrings: should describe each building block in concise purpose-first language.

  ***acceptance tests***

  - Each wrapper description states what it transforms.
  - Each wrapper description states what it preserves.
  - Each wrapper description states which downstream training use case it supports.

- :WrapperDocstrings: should capture the generalized roles of concrete wrappers without using benchmark names as the primary taxonomy.

  ***acceptance tests***

  - A compact coordinate-state environment maps to a finite-state observation-wrapper role.
  - A Gym API environment adapter with max-step support maps to a Gym adapter role with truncation support.
  - A task-definition environment over raw dynamics maps to reward and termination wrapper roles.
  - A discretized observation environment maps to a discretized observation role.
  - A feature-based Gym adapter with action mapping maps to action, feature, and Gym adapter roles.
  - `Monitor` and `VecMonitor` map to a monitoring wrapper role.
  - `RecordVideo` maps to a recording wrapper role.
  - `SubprocVecEnv` and `DummyVecEnv` map to a vectorization adapter role.
  - `LoggerCallback` maps to a training callback role.
  - `RecordEvalEpisodeCallback` maps to an evaluation callback role.
  - `make_lunar_env`-style constructors map to an environment factory role.

- :WrapperReference: should provide the generalized building blocks as plain descriptions.

  ***acceptance tests***

  - :IndexWrapper: is described as mapping finite structured state into tabular observation indices.
  - :FeatureWrapper: is described as exposing engineered features for approximation-based learners.
  - :ActionWrapper: is described as converting agent action codes into lower-layer control values.
  - :RewardWrapper: is described as turning domain evaluation logic into scalar learning signal.
  - :TerminationWrapper: is described as defining task success and failure boundaries.
  - :TruncationWrapper: is described as enforcing external episode budgets.
  - :GymWrapper: is described as standardizing the training interface for RL libraries.
  - :MonitoringWrapper: is described as attaching episode statistics or diagnostics without changing task semantics.
  - :RecordingWrapper: is described as capturing rollout media for debugging or reporting.
  - :VectorizationAdapter: is described as batching multiple environment instances behind one training-facing interface.
  - :EnvironmentFactory: is described as constructing configured environment instances separately from algorithm logic.
  - :TrainingCallback: is described as observing or logging training progress without redefining environment semantics.
  - :EvaluationCallback: is described as triggering periodic evaluation on a separate environment without changing the training environment contract.

- :TrainingEnvironment: should be the only object that downstream algorithms depend on directly.

  ***acceptance tests***

  - Training code can be written against the outermost interface without knowledge of lower wrapper details.
  - Wrapper composition changes do not require rewriting the learning algorithm when the outer contract is preserved.

- :WrapperLibrary: must not force unrelated concerns into one monolithic environment class.

  ***acceptance tests***

  - Observation encoding can be changed without rewriting reward logic.
  - Reward logic can be changed without rewriting action mapping.
  - Truncation can be added or removed without rewriting the base environment.
  - Monitoring can be added or removed without rewriting task-definition logic.
  - Recording can be added to evaluation without rewriting the training stack.
  - Vectorization can be added or removed without redefining the underlying task semantics.

- :WrapperLibrary: should make wrapper composition inspectable.

  ***acceptance tests***

  - A user can identify the lower wrapped object of each wrapper layer.
  - A user can tell which layer owns observation encoding, reward computation, termination, and truncation.
  - A user can identify whether monitoring, recording, or vectorization are present as infrastructure layers rather than task-definition layers.

- :WrapperLibrary: should preserve debugability for teaching and experimentation.

  ***acceptance tests***

  - A lower-layer environment can still be inspected directly when needed.
  - A wrapper stack can surface informative metadata through `info`.
  - The system supports comparing raw-state and transformed-observation views of the same task.
  - The system supports keeping training and evaluation environments separate when recording or other eval-only infrastructure is needed.
