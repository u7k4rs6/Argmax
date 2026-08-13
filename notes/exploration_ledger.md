# Exploration ledger for phase margin-v1

Every exploratory analysis run against this phase's store, with the problems
it could have seen and when. Written **before** `post_run.py`, which reports
over the whole set and would expose everything.

Why this exists: the sampler iterates problem-major, so the set of problems
available to an analysis is a **prefix** of the sampling order. Every
exploratory look therefore landed on the early problems and never touched the
late ones, which creates an unexamined holdout nobody designed. That holdout is
the only route to a confirmatory margin-gate claim inside the remaining $2.55,
because a fresh confirmatory run over 198 problems costs $3.45.

Exposure is counted **conservatively**: a problem is exposed if any sample of
it was in the derived table when an analysis ran, even if that analysis used
complete problems only. Pooled statistics over all rows, such as the margin
distribution, did include partial problems.

## What each analysis could see

| analysis | ledger rows at run time | problems exposed |
|---|---|---|
| margin distribution | ~6900 | 108 |
| plurality, correctness and tail splits | ~7750 | 122 |
| bootstrap split differences and three-way join | ~8400 | 129 |
| Qwen-only correlation | ~8894 | 129 |

The three-way correlation additionally used only the 30 problems that overlap
the predecessor's phase 14b probe, but its exposure is the full prefix above,
because the join was computed from the whole derived table.

**Exposed set: 129 problems.** They are burned for any confirmatory
purpose on this store.

## The holdout

**69 problems have never appeared in any exploratory analysis.**
They were not sampled until after the last look, purely because of
problem-major iteration. Their ids follow. They are recorded here and
**not analysed**: listing them is what makes the holdout auditable, and looking
at them is what would destroy it.

```
77ec494f9b944bb0cba916b2351235ca
3f833b7639a1fa2676188884c700b715
2b6b5fc033aed6068221e0ba887adb3f
29cf938fabcca31cc5e549736c515e7f
d11b6e08d8a57141f3d28edc7174ad25
fc36199524f2462339a81f2a48ae8223
1e74c083789870eaa9abc34aefa49c0a
be06de2777652bfbc679f3d0f9d68ee9
09f8a0c977c236c48a7a337c0e1f5825
92f21c5760867bbe8651182422926924
8f8491ad0706e3b2f3b92d2464500554
03ed1a36aa4b56b165908d84ae276bf1
f6e13dbbd7f8926865969027d31a4db0
8bf1bba6b9096f5d0afd6c672b0a5d94
33f93a7d8d7c058646e2c11a3fbffaf6
ca030d622626d1301c71297a032c8b6b
016bfd0f9bf6b0d84f413fb58163f85b
36b9f11caa02a45fa7dcc490b055ab37
1aaa776365e4be9c266079122b6b4944
68fc43bf1b13e26ccb169648156cd895
653ad1ee18a9a79762bb4e106e7cc6d9
8e58b6ea8a29f788abbe37fefc542633
51521c294f711bf7ef0c9dfeea51ab85
d34a34178e6ffd75ac75f498953668f8
eaeb10032627185c3bdb2db99ca1bb45
f3908e2b8ae20b32f047103704bdfe11
72d7e3da64849f84588472d8524bce0f
5767a1f03a62af0ca0106f55c309eae8
d0b0962caf44d5227e640b0f452e8aa0
0cd5863983cd7213b29dddf0b399e016
74b2284e2b9e8f13c5ae083453695d23
3f15743da2b27949583eebe03096159d
61731f13c201cb6125e1d02e447d5cc9
3e2b64db4a3836aeb990d0784a37557a
bd44a2e4097659f1aeac335e23bbaaf8
5c2cadb5423bed6ced78a437991d8ff2
0499ef294c3d863e83f444540f415fd7
ccb41b3397bd40852500f3b5852d6eb9
70802e7a6b9b47a623b3cfee8a624e5f
469d0c35d15fb97e71b6b221021e9a60
2fbcf755c066a9363c6607fd9809447b
9751db402e42df09d8416bd92f29be01
c7710b512c9b1c301fb2982e87daaace
165e872fd4e99ba00f1c963c246ca468
3cd9e69fb60d1ce527abe299198c12fc
1ae80bd86ccff8a9aff459e34db517b6
bd22a2d99a49d9f7c1ac4de82eaa4ed0
1e9819340c7d9b6651805344116fe9e0
b6d98cda8302aad6828bc3d9dbc1c3a3
d931c85d494677b19cbb4cac4aa13496
c83f1ee46ac8e7b7199866b0ac4a12d8
4e23c2831ba622d81fa8c051e94569c6
da89e1b8221a2f1765d21ee57a502dc2
953cfec4a41ef1ad2c25c32155a3a1b0
245580d098df082ebd6fd79c71d57ab3
e8efe1e42e257a2e064a4e664c14310a
84890616e8e1446eca6ca004949dc11b
4479cd0320622f65376432d009ca4c6d
3e9a57bead21be8fb50fd305119618cc
873f2af11b045e9d0a3eb6188917eb20
a1fe38547ffc08c2165a310b928f6b57
7543d39d5b81d5015a675340a2a20352
35b0e0b3c6609cb4e9d50f9358bed8a6
8e87fcb5a90c86dc8bd747a82be07166
f42ac9ab4935a6720e78476a537fc84b
f11993de73db9e06fd4fc4bfeb765734
c5fdd6103ea012dfc42d41033a03f4c7
aa3c24c4530e34f465ce396712080232
e4e894cbc3100d8c02b0fb24c5f42fe4
```

## Can the holdout carry a claim?

The resolution check, run before any decision and using variance measured on
the **exposed** problems only, so the holdout stays untouched:

| quantity | sd across exposed problems | MDE at n=69 |
|---|---|---|
| per-problem accuracy | 0.3052 | **0.1029** |
| sub-2-nat tail fraction | 0.0641 | **0.0216** |

Minimum detectable effect at alpha 0.05 two-sided and 80 percent power.

**What that means, stated before anything is registered.** A per-problem
accuracy effect must exceed **10.3 points** to be detectable on this holdout.
For scale, the entire aggregate curve on the confirmatory 151 spans 0.52
points, and the estimator advantage TA1 resolved was 2.1 points. A holdout of
69 problems cannot resolve effects of the size this project has
been measuring.

The tail fraction is better placed at 2.2 points, but no margin-gate hypothesis
has been written in terms of it.

**So the holdout is real, auditable and probably too small for the claim it
would be spent on.** That is a finding about what the remaining $2.55 can buy,
and it is the kind of thing to establish before registering rather than after.
Nothing is registered against it here.

## Exposure on the margin-v2 store, and what stays unread

Added after v2 was registered and sampling. This ledger began as a record for
margin-v1; the same discipline applies to v2 and is recorded in the same
place rather than in a second file that would have to be cross-read.

**v2 has no exploratory prefix.** Unlike v1, no analysis ran against it while
it drew. Its 198 problems were clean at the moment it was registered and its
tag was cut before a single sample existed.

What its own run report exposes, and what it does not. Exposure is
**analysis-specific** under doc 2 section 8.1: an analysis exposes the
question it asked, not every question that could be asked of the columns it
touched.

| quantity on the v2 store | status |
|---|---|
| MD3 and MD4, per the registered claims | confirmatory, one look, `argmax-prereg-margin-desc-v2.0` |
| answer rate, truncation, cost | run diagnostics, exposed |
| margin distribution | exposed, and registered claims are computed from it |
| survivor count and accuracy distribution | exposed, required beside the pooled figures by doc 2 section 7.2 |
| **completion length, marginal only** | **exposed**, reported as an exploratory run diagnostic and labelled so |
| **completion length crossed with per-problem accuracy** | **UNREAD** |
| **completion length crossed with curve shape or peak N** | **UNREAD** |
| **completion length crossed with whether a problem backfires** | **UNREAD** |

The three unread rows are the joint that `notes/completion_length_candidate.md`
identifies as the durable question. **They are preserved deliberately.** The
marginal was reported because a paid confirmatory run's diagnostics are not
optional; the joint was not, because nothing required it and reporting it
would have spent the only clean set this project has left on a hypothesis
whose design is not done.

The confound check in that note's section 5, length against accuracy, was run
on the **v1 exposed 129** for exactly this reason. It is not repeated on v2
and must not be.

A future registration over the v2 store therefore states that the length
marginal was seen and the joint was not. That is a weaker constraint than a
burned set, and it is the sort of thing a registration discloses rather than
something that forecloses one.
