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

  **This is a tension to address, not a citation to drop in.** Either the
  difference is the setting (a 7B non-reasoning model on GPQA Diamond at
  temperature 0.7, against frontier models), or the unit (per-sample margin
  against calibrated per-question confidence), or the conditioning (dissent
  from a self-consistency plurality against objective correctness). The draft
  has to say which it thinks, and it cannot claim log-probs are uninformative
  in general on the basis of one model.

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
