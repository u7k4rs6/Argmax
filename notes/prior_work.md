# Prior work: what is novel here, searched adversarially

Written to find the paper that scoops us, not to confirm none exists. The
short version is at the top because it changes the draft's framing rather
than adding a citation to it.

## Verdict

| our result | status | closest prior work |
|---|---|---|
| **dilution**: sequence-averaged confidence is dominated by high-confidence filler tokens | **KNOWN. Not a contribution.** Stated as a motivating premise, not a finding, since 2023 | Duan et al., SAR, arXiv:2307.01379, ACL 2024 |
| **localization is the fix**: measure confidence at the answer span | **KNOWN.** Several independent lines already do this | SAR; DeepConf; claim-conditioned probability; CIKM 2025 "One-Token Deep" |
| **commitment**: a sample contradicting its own problem's plurality is as saturated as one agreeing with it | **not found in this form.** The nearest paper reaches a contrasting conclusion | Kumaran, arXiv:2606.29490 |

**The dilution half is folklore and the draft must not lead with it.** It is
worse than merely known: it is the *premise* of a 2024 ACL paper, which means
by 2024 it was already taken as established enough not to need demonstrating.
A draft that opens by showing mean token entropy is diluted by prose is
opening with a restatement.

## 1. Dilution: established, and older than it looks

**Duan et al., "Shifting Attention to Relevance" (SAR), arXiv:2307.01379, ACL
2024** is the direct hit. Its motivating observation is ours: tokens do not
contribute equally to meaning, and uncertainty estimators that average over
all of them let semantically empty tokens dominate. The paper's own framing is
that existing methods weight tokens "equally or even heavily" when those
tokens carry "very limited semantics", under the heading of linguistic
redundancy. SAR then fixes it by weighting tokens by how much removing them
changes the sentence embedding.

Note what that means for us. SAR does not *discover* dilution. It assumes it,
demonstrates it is costly, and ships a correction. Our 1/613 arithmetic is a
sharper instance of a premise someone else already built a method on top of.

The root is older still. Sequence log-probability's length pathology is
long-standing in the machine-translation literature, where cumulative log
probability falls monotonically with length and biases search toward short
outputs, with per-token normalization as the standard remedy and its own
over-correction as a known follow-on problem (Murray and Chiang,
arXiv:1808.10006). "Averaging a log probability over tokens produces a number
about fluency rather than about the answer" is a restatement of that in a new
setting. There is also recent work explicitly on removing the length
dependence of LLM uncertainty estimates (arXiv:2505.19060).

The same concern motivates the semantic-uncertainty line: the reason to
cluster by meaning rather than score surface sequences is that surface tokens
are not where the answer lives.

### What our arithmetic adds, honestly

Very little, and the draft should say so rather than dress it up:

- It is a **measured instance with a number attached** on a specific store,
  613 tokens averaged with the answer token being one of them, rather than a
  qualitative premise.
- It is a **failure of a deployed gate**, observed after the gate was built and
  thresholded, rather than a motivating example chosen to introduce a fix. The
  entropy gate failed on aggregation and the arithmetic explains why.
- It is on **multiple choice with a single answer token**, where the dilution
  ratio is at its most extreme and the arithmetic is exact rather than
  approximate. SAR's setting is free-form generation where "the relevant
  tokens" is itself a modelling problem.

That is a worked example and a diagnosis of one of our own failures. It is not
a finding. **Anyone who has read SAR will consider this half already made.**

## 2. Localization: also known, by several routes

The fix does not rescue the novelty either. Measuring confidence somewhere
other than the whole-sequence average is well populated:

- **SAR**, relevance-weighted tokens.
- **DeepConf**, group confidence over sliding windows rather than the full
  trace, used to prune reasoning traces at test time.
- **Claim-conditioned probability**, restricting to the tokens carrying the
  claim.
- **"Uncertainty Quantification for Multiple-Choice Questions is Just
  One-Token Deep"**, CIKM 2025, doi 10.1145/3746252.3760887, which is
  explicitly about the answer-token locus in multiple choice. Its actual
  claim is a fragility result, that fine-tuning on 1,000 examples to shift the
  first generated token's distribution distorts a wide range of UQ methods
  while leaving accuracy unchanged. Different claim from ours, same locus, and
  the title alone will make a reviewer ask what we add.

So both the diagnosis and the obvious fix are taken.

## 3. Commitment: not found, and one paper points the other way

**Our claim.** MD1 and MD2, registered and passed on an unexamined holdout: a
sample whose answer contradicts its own problem's plurality still emits that
answer at a median margin of 20.5 nats, with 71 percent above 10 nats at the
lower bound. Samples that dissent are as saturated as samples that agree. The
implication is that the disagreement self-consistency exploits does not live
at the answer token at all. It lives upstream, in which chain got written, and
the answer token is a near-deterministic readout of a chain already committed.

**I did not find this shown.** Adjacent work exists and none of it is the same
claim:

- **Kumaran, "Reported Confidence in LLMs Tracks Commitment More Than
  Correctness", arXiv:2606.29490 (June 2026).** The nearest title, and it is
  about **verbal** confidence, not token log-probabilities. Its finding runs
  the other way for us: verbal confidence predicts a later commit-or-abstain
  decision better than it predicts correctness, while **calibrated token
  log-probabilities behave as an "answer-evidence signal"** whose ability to
  predict abstention is coupled to its ability to discriminate correctness.
  So it reports that log-probs *do* track correctness, on a two-stage
  abstention paradigm over SimpleQA, MMLU-Pro, SuperGPQA and HLE.

  **Reconciled, on the unit, after reading the paper rather than its
  abstract.** Kumaran's Cal-LP is our quantity: a temperature-scaled softmax
  over the option letters at the answer position, calibrated on a held-out
  set. So the locus matches exactly and the disagreement cannot be explained
  away as measuring different things. What differs is the unit the claim is
  over. Every Cal-LP result in that paper is **trial-level and across
  questions**: Phase 1 produces **one** answer per question, the reported
  statistic is AUROC over trials, defined there as the probability that a
  randomly chosen correct trial receives higher confidence than a randomly
  chosen incorrect one, and Cal-LP reaches 0.62 to 0.80 on that. Self
  consistency does not appear in the design, no question is sampled more than
  once in Phase 1, and **the paper never conditions on samples that disagree
  with each other**, because it never has two samples of the same question to
  compare. Our claim is the orthogonal one: **within** a question, across
  samples that already disagree, the answer token cannot say which to trust.
  Our own data agrees with Kumaran on his unit and we must say so, since the
  fraction above 10 nats separates correct from incorrect samples by +0.0589
  with an interval excluding zero. **So there is no conflict, and the draft
  must not claim log-probabilities are uninformative.** The claim is that a
  signal with real across-question discrimination is close to useless for the
  within-question routing decision self-consistency actually poses, which is
  a statement about where the variance sits and not about whether the signal
  carries any. Kumaran is a supporting citation for the setup and a
  correction to any stronger phrasing.

- **"Models commit early in the reasoning chain"** work, where later tokens
  are reported to have diminishing causal influence on the final answer. That
  is consistent with our reading and is about causal influence of reasoning
  tokens, not about the confidence of the answer token conditioned on
  dissent.

- **Weighted majority voting** work observes that logprob-derived confidence
  "often fails to separate correct from wrong traces on difficult problems".
  That is the same phenomenon seen from the application side and stated as a
  practical limitation. Nobody in what I found measured the margin
  distribution conditioned on plurality dissent and reported it as the
  finding.

**So the contribution is here, if it is anywhere.** Not that averaged
confidence is diluted, which is known, and not that one should localize, which
is done. That **localized confidence, measured correctly and cheaply, is still
uninformative about the disagreement self-consistency runs on**, because the
answer token is saturated whether the sample is in the majority or the
minority. The dilution result becomes the setup: it explains why the obvious
fix was worth trying and rules out "you measured it in the wrong place" as the
reason it failed.

## 4. What this does to the framing

1. **Do not open with dilution.** Cite SAR and the length-normalization
   literature, state in two sentences that averaging dilutes, and move on. Any
   more space than that reads as not having done the reading.
2. **Lead with the commitment result**, which is the registered, held-out,
   passed claim and the one with no located predecessor.
3. **The 1/613 arithmetic becomes methods, not results.** It justifies
   measuring at the answer span, which is what makes the commitment result
   interpretable rather than an artefact of bad instrumentation.
4. **Engage arXiv:2606.29490 directly.** It is recent, it is from a strong
   group, and a reviewer will know it. Ignoring a paper that reports
   log-probabilities tracking correctness while we report answer-token
   saturation under dissent would be the kind of omission that sinks a
   submission.
5. **The reasoning wall stays a separate contribution.** Three models, three
   measured refusals, and a cap-comparability result. Nothing in this search
   touched it.

## How hard I looked, and the limits of that

Searched: token-relevance and dilution in uncertainty estimation; length
normalization pathologies in sequence confidence; answer-span against
sequence-averaged confidence; calibration under chain-of-thought; self
consistency with minority and majority samples under logprob confidence.
Followed the strongest hits to source, and read arXiv:2606.29490 directly
rather than trusting a summary of it, which mattered: an automated summary of
that paper reported it as measuring answer-token logprobs against
self-consistency dissent, and its abstract says something close to the
opposite.

**A negative literature result is weak evidence.** I ran a search, not a
survey. The commitment result is "not found by me", not "novel". The two
positive results in section 1 and 2 are the reliable half of this note: those
papers exist and say what they say.

## 5. The reasoning wall, searched with the same aggression

It was the only unexamined contribution. It is now partly examined and partly
taken.

### Taken: budget-dependent rankings, on our exact benchmark

**"Who Thinks Best Depends on How Long You Let Them: Budget-Dependent
Rankings in LLM Evaluation", arXiv:2608.12150.** The uncomfortable one. Same
benchmark, GPQA Diamond at 198 items, alongside GSM8K and MATH-500. Its
finding is that model rankings **reverse** across token budgets on every
benchmark with reversals significant at p < 0.01, with LLaMA-3.3 70B leading
at budget 256 and GPT-OSS 20B dominating at 4096 on GSM8K. It also handles
truncation as a confound directly, with a three-tier analysis over all items,
per-model completed items, and items every model completed, and reports that
the effect survives the filtering.

**That is our cap-incomparability result, established more thoroughly than we
establish it, on the same benchmark.** Anyone reviewing us will know it. We
must cite it as the finding and position ourselves against it, not restate it.

### The gap it leaves, and it is exactly ours

The paper **deliberately excludes reasoning-native models**, naming o1,
DeepSeek-R1 and QwQ, on the stated grounds that their dual-stream
architecture changes the semantics of `max_tokens`. Its four models are
LLaMA-3 8B, Qwen-3 32B, LLaMA-3.3 70B and GPT-OSS 20B.

So the strongest prior work on budget-dependent evaluation carves out
precisely the class we measured, and carves it out for the reason our result
is about. We measure what happens in the excluded region: at cap 2048 and
4096 a reasoning-native 9B model returns answer rate 0.0000 with mean
completion **equal to the cap exactly**, which is not a ranking reversal but
the total collapse of the measurement, and it is what "the semantics of
`max_tokens` change" looks like when someone runs it.

### Also established, and only worth a sentence each

- **Token budgets move benchmark accuracy a great deal.** Widely reported,
  including 30-point swings from a harness default of `max_new_tokens=128`.
  Not novel.
- **Truncated outputs scored as incorrect bias comparisons downward**, and
  models with different truncation rates are not comparable at a fixed cap.
  Stated in the evaluation-validity literature. This is the premise of our
  answer-rate rule, not a finding of ours.
- **Model deprecation and endpoint churn break replication.** Covered
  squarely, for instance arXiv:2512.00651 on LLM-for-software-engineering,
  which already recommends disclosing API version and access date and
  including an open-weights baseline "if commercial endpoints disappear".
  Our four `model_not_available` refusals are an instance of a known problem.
- **Evaluation cost as a barrier** is documented at the other end of the
  scale, with figures like $40,000 for one multi-model benchmark effort.

### What survives as ours

Three things, and the draft should claim only these:

1. **Measurements inside the excluded region.** Three reasoning-native models,
   three distinct walls, each measured by real request rather than inferred:
   unreachable, answering at 0.6460 only at 16,384, and 0.0000 at any
   affordable cap. arXiv:2608.12150 says the semantics change; we report the
   numbers.
2. **Comparability keyed on answer rate rather than on matched caps**, stated
   as a rule with a test behind it rather than as a filtering step applied
   once. Their three-tier analysis is the same instinct applied post hoc; ours
   is a design constraint applied before sampling, which is why cap 6144 was
   chosen for a second model against a first model's 2048.
3. **The cost of establishing a negative, reported.** arXiv:2608.12150
   mentions 56,476 API calls and reports **no monetary cost at all**. We
   report $0.1347 over 148 probe samples against a $0.15 ceiling, and a full
   ledger. In a literature where the cheap-versus-frontier gap is the reason
   small groups cannot replicate anything, an itemised bill for a negative
   result is a contribution in itself, and it is the one nobody else here is
   making.

**Downgrade the framing accordingly.** The reasoning wall is not "we
discovered reasoning models cannot be evaluated cheaply". It is "the standard
budget-comparability result excludes reasoning-native models by construction,
here is that region measured, and here is what it cost".
