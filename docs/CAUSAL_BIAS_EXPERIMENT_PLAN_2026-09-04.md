# Causal Length and Style Bias Experiment

Date drafted: 2026-09-04

## Motivation

The existing winner-versus-loser word-count comparison is observational.
Longer arguments may also differ in model identity, content, evidence, topic,
or quality, so an association between length and winning does not establish a
verbosity bias. This experiment uses paired counterfactual transcripts to vary
length or tone while holding the debate's substantive content and all design
factors as constant as text editing permits.

## Source Sample and Assignment

Reuse the frozen 120-transcript sample from Experiment 2. Before reading any
counterfactual verdict, deterministically assign one focal debater per
transcript using a recorded seed. The assignment must balance focal model,
candidate slot, proposition, starting status, and topic. The opponent, turn
order, propositions, and candidate presentation order remain unchanged across
every variant of a transcript.

### September report phase

To fit the September 15 deadline without using incomplete data, the report
phase uses 100 debates from the already validated 240-debate paper dataset.
Selection requires at least a 5% original relative length difference and is
fixed without reference to any verdict. The tracked manifest contains exactly
ten debates per topic, 25 focal assignments per debater, 50 focal assignments
to each candidate slot and proposition, 50 starting and 50 non-starting focal
debaters, and 50 compression and 50 expansion interventions. The four original
debater models serve as the forced-choice judges, so this phase also uses the
same model set for debating and judging. Each judge evaluates both the original
and accepted matched-length transcript. Tone intervention remains part of the
PLOS extension unless it can be completed and audited after the report-priority
experiments.

## Intervention A: Matched Length

Rewrite only the focal debater's four turns. The target is the opponent's total
word count, with total and per-turn tolerances fixed before generation. Preserve
the function of each turn and every claim, evidence item, example, number,
concession, and rebuttal. Do not add new facts, arguments, citations, or attacks.
Record whether matching required compression or expansion and the achieved word
counts. Compare the accepted variant with the canonical modal verdict from the
three-repeat robustness condition.

For the September report phase, both the original and matched-length versions
receive fresh forced-choice judgments from the same four-model panel. This
provides a directly paired baseline without relying on the earlier
tie-permitting judgments.

## Intervention B: Matched Tone

Create two versions of the same focal turns:

1. direct and assertive, without adding certainty to factual claims; and
2. cautious and hedged, without retracting or weakening substantive claims.

The two variants must have matched total and per-turn word counts within a
pre-specified tolerance. They must preserve the same content and differ only in
linguistic presentation. Compare the two variants directly rather than treating
the original, uncontrolled style as a neutral baseline.

## Transformation and Acceptance

Use one fixed strong rewriter with a versioned prompt, temperature, token limit,
and model identifier. Store the original and rewritten turns, prompt hash,
target and achieved counts, retry number, and timestamp.

A variant enters judging only if it passes all of the following:

- exactly four focal turns in the original locations;
- target word-count tolerance and no empty or degenerate text;
- unchanged position and no candidate or judge references;
- preservation of numbers, named entities, examples, claims, and rebuttals;
- no new factual content, evidence, citation, or argument; and
- acceptance by two independent semantic-preservation verifiers.

Freeze the verifier models, rubric, acceptance threshold, maximum retries, and
exclusion rule before transformation. Manually audit a seeded subset without
seeing judge outcomes. Report verifier agreement, retries, exclusions, and the
manual audit result.

## Judging

Use the same six-model forced-choice judge panel as the other final-report
experiments. Within a transcript, preserve candidate labels and presentation
order across paired conditions. Reuse the canonical modal result for the length
baseline; collect one judgment per judge for each accepted matched-length,
assertive, and cautious variant. Record exact prompt and transcript hashes.

Planned maximum before exclusions:

- 120 matched-length rewrites;
- 240 tone rewrites;
- 720 matched-length judgments; and
- 1,440 tone judgments.

Verifier and retry calls are reported separately from scientific observations.

## Primary Analysis

For length, report the paired change in focal-candidate selection from canonical
modal judgment to matched length. Stratify by compression versus expansion and
report each judge separately. For tone, report the paired change in focal
selection between assertive and cautious variants. In both analyses, report
winner-flip counts, percentage-point effects, paired tests, and bootstrap
intervals clustered by transcript. A pooled model may include judge fixed
effects, but it does not replace judge-specific results.

Secondary analyses may examine heterogeneity by debater and original length
gap only if clearly labeled and uncertainty is retained. Do not select examples
or transformations based on verdicts.

## Interpretation Limits

The causal claim is limited to accepted counterfactual rewrites under these
prompts. Semantic equivalence cannot be guaranteed perfectly, expansion and
compression may affect clarity, and post-hoc edits may slightly alter discourse
naturalness. The report must distinguish these intervention effects from a
universal causal effect of verbosity or style.
