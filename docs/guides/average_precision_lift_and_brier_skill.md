# ROC-AUC, Average-Precision Lift and Brier Skill

This guide explains three measures used in the thesis. Each answers a different question:

| Question | Measure |
|---|---|
| How often does the model rank an event observation above a non-event observation? | ROC-AUC |
| Does the model concentrate event observations near the top of the risk list? | Average-precision lift |
| Are the predicted probabilities close to the outcomes that actually occur? | Brier skill |

The first two measures evaluate ranking from different perspectives. Brier skill evaluates the probability scale. A model may rank companies well while giving probabilities that are much too high. Such a model may help order a review queue, but its probabilities should not be used directly in a monetary credit-limit formula.

## 1. Average Precision: Are Events Near the Top?

Imagine that the model sorts all company-months from highest to lowest predicted risk. A useful model should place observations followed by a disclosure event near the top of that list.

Average precision summarizes how well the model does this across many possible alert cutoffs. It is based on:

- **Precision:** of the observations flagged by the model, how many are followed by an event?
- **Recall:** of all observations followed by an event, how many did the model flag?

For example, if the model creates 100 alerts and 5 are followed by an event, precision is 5%. If there are 20 event observations in total and the alerts contain 5 of them, recall is 25%.

Average precision combines the precision and recall obtained as the cutoff moves down the ranked list. It is therefore not the precision at one particular cutoff.

### How moving the cutoff works

Consider five observations ranked from highest to lowest predicted risk. Two are followed by an event:

| Risk rank | Event observed? | Observations flagged if the cutoff stops here | Precision | Recall | AP contribution |
|---:|---|---:|---:|---:|---:|
| 1 | Yes | 1 | 1/1 = 100% | 1/2 = 50% | 50% × 100% = 50.0% |
| 2 | No | 2 | 1/2 = 50% | 1/2 = 50% | 0% × 50% = 0.0% |
| 3 | Yes | 3 | 2/3 = 66.7% | 2/2 = 100% | 50% × 66.7% = 33.3% |
| 4 | No | 4 | 2/4 = 50% | 2/2 = 100% | 0% × 50% = 0.0% |
| 5 | No | 5 | 2/5 = 40% | 2/2 = 100% | 0% × 40% = 0.0% |
| **Total AP** |  |  |  |  | **83.3%** |

At the first cutoff, only the highest-risk observation is flagged. Precision is 100% because it is an event, but recall is only 50% because one of the two events has been found. Lowering the cutoff to include the second observation adds a non-event, so precision falls while recall stays unchanged. Lowering it again includes the second event, bringing recall to 100%.

The AP contribution is the increase in recall multiplied by precision at that cutoff. Rows that do not find another event have no increase in recall and therefore contribute zero. In this example, each discovered event increases recall by 50 percentage points:

$$
AP=(0.50\times1.00)+(0.50\times0.667)\approx0.833.
$$

The average precision is therefore approximately 83.3%. If both events appeared at the first two positions, it would be 100%. If they appeared near the bottom, precision would be lower when they were found, producing lower average precision.

More generally, the calculation is:

$$
AP=\sum_n (R_n-R_{n-1})P_n,
$$

where $P_n$ is precision at a cutoff and $R_n-R_{n-1}$ is the increase in recall at that cutoff. Cutoffs that add only non-events do not increase recall, but they can lower the precision available when the next event is found.

### Why the event share matters

When events are rare, average precision can look numerically small even when the ranking contains useful information. Suppose only 2 of every 1,000 observations are positive. The event share is 0.2%, and an uninformative ranking is expected to have average precision close to 0.2%.

An average precision of 0.9% may still look low, but it is more than four times the 0.2% baseline. Average precision should therefore be interpreted relative to the event share.

## 2. Average-Precision Lift

Average-precision lift makes that comparison directly:

$$
\text{AP lift}=\frac{\text{average precision}}{\text{event share}}.
$$

Interpretation:

- **AP lift = 1:** approximately the same ranking quality as an uninformative ranking;
- **AP lift > 1:** positive observations are concentrated nearer the top of the list;
- **AP lift < 1:** the ranking is worse than the event-share baseline.

### Simple example

Suppose the event share is 2% and average precision is 8%:

$$
\text{AP lift}=\frac{0.08}{0.02}=4.
$$

Average precision is four times the event share. This does **not** mean that the model is four times more accurate, that every alert has 8% precision, or that the model detects four times as many events at one fixed cutoff. It describes ranking performance across cutoffs.

## 3. ROC-AUC: How Often Is an Event Ranked Higher?

ROC-AUC also evaluates ranking, but it uses a different idea from average precision. It considers every possible pair containing:

- one observation followed by an event; and
- one observation not followed by an event.

For each pair, it asks whether the model gives the event observation a higher risk score. ROC-AUC is the share of pairs ordered correctly. A tied score counts as half a correct pair.

Interpretation:

- **ROC-AUC = 1:** every event observation is ranked above every non-event observation;
- **ROC-AUC = 0.5:** ranking is no better than random ordering;
- **ROC-AUC < 0.5:** the ordering is generally reversed.

### Pairwise example

Use the earlier five-observation ranking. Events are at ranks 1 and 3, while non-events are at ranks 2, 4 and 5. This creates six event/non-event pairs:

| Event observation | Non-event observations ranked below it | Correct pairs | Possible pairs |
|---|---|---:|---:|
| Event at rank 1 | Ranks 2, 4 and 5 | 3 | 3 |
| Event at rank 3 | Ranks 4 and 5, but not rank 2 | 2 | 3 |
| **Total** |  | **5** | **6** |

Therefore:

$$
\text{ROC-AUC}=\frac{5}{6}\approx0.833.
$$

The model has an 83.3% chance of assigning a higher score to a randomly selected event observation than to a randomly selected non-event observation.

### ROC-AUC versus average precision

Both measures use the ranking, but they emphasize different aspects:

- ROC-AUC evaluates all event/non-event pairs across the complete ranking.
- Average precision gives more attention to how many events appear near the top, where alerts would normally be created.

ROC-AUC is not directly determined by the event share. It can therefore look strong even when precision remains low in a very rare-event problem. This thesis reports both ROC-AUC and average precision, but uses average-precision lift rather than ROC-AUC as the first tuning criterion.

## 4. Brier Score: Are the Probabilities Reasonable?

Ranking is not enough when the predicted probability enters a credit-limit calculation. A company assigned 20% risk should not actually behave like a group with only 2% observed events.

The Brier score measures the difference between each predicted probability and the observed result:

$$
BS=\frac{1}{N}\sum_{n=1}^{N}(q_n-y_n)^2,
$$

where:

- $q_n$ is the predicted probability;
- $y_n=1$ when the event occurs and $y_n=0$ otherwise; and
- $N$ is the number of observations.

The difference is squared, so large probability mistakes receive a larger penalty.

### One-observation examples

If the model predicts 2% and no event occurs, the error is:

$$
(0.02-0)^2=0.0004.
$$

If the model predicts 2% and an event occurs, the error is:

$$
(0.02-1)^2=0.9604.
$$

The Brier score is the average of these errors across all observations. Lower is better, and zero is perfect.

A small Brier score is not automatically impressive when events are rare. A model that assigns a very low probability to everyone can have a small score because most observations are negative. The score must therefore be compared with a simple reference prediction.

## 5. Brier Skill: Is the Model Better Than the Reference?

Brier skill compares the model's probability error with the error from a reference prediction:

$$
\text{Brier skill}=1-\frac{BS_{model}}{BS_{reference}}.
$$

Interpretation:

- **Brier skill = 1:** perfect probability predictions;
- **Brier skill > 0:** less probability error than the reference;
- **Brier skill = 0:** the same probability error as the reference;
- **Brier skill < 0:** more probability error than the reference.

### Simple example

Suppose the reference Brier score is 0.010 and the model's score is 0.008:

$$
\text{Brier skill}=1-\frac{0.008}{0.010}=0.20.
$$

The model reduces Brier error by 20% relative to the reference.

The reference must always be identified. In each thesis tuning fold, the reference assigns every validation observation the event rate from the preceding fitting data. This represents the simple strategy: “give every company the same probability based on past frequency.”

Brier skill can be strongly negative. For example, a value of -2 means that the model's Brier error is three times the reference error:

$$
-2=1-\frac{BS_{model}}{BS_{reference}}
\quad\Longrightarrow\quad
\frac{BS_{model}}{BS_{reference}}=3.
$$

## 6. Step-by-Step Example from the Thesis

The first temporal tuning fold uses 2011–2016 for fitting and 2017 for validation. The following values come from the unweighted logistic-regression candidate.

### Step 1: Establish the reference probability

The fitting data contain 294 positive observations among 196,174 observations:

$$
\frac{294}{196{,}174}\approx0.001499=0.1499\%.
$$

The constant reference therefore assigns approximately 0.1499% probability to every 2017 validation observation.

The 2017 validation data contain 58 positive observations among 26,265 observations:

$$
\frac{58}{26{,}265}\approx0.002208=0.2208\%.
$$

The event share increased from about 0.1499% in the fitting data to 0.2208% in the validation data.

### Step 2: Evaluate overall ranking with ROC-AUC

The logistic model's 2017 ROC-AUC is 0.7706. In pairwise terms, this means that an event observation receives a higher predicted score than a non-event observation approximately 77.1% of the time. This is better than the 50% expected from random ordering, but it does not show whether the highest-risk alerts have useful precision.

### Step 3: Evaluate rare-event ranking with average-precision lift

The model's 2017 average precision is 0.9033%. Its lift is calculated against the 2017 event share:

$$
\text{AP lift}=\frac{0.0090327}{0.0022083}\approx4.09.
$$

Although average precision is below 1% in absolute terms, it is 4.09 times the event-share baseline. This indicates useful ranking information in a very rare-event setting.

### Step 4: Evaluate probability error with Brier skill

The constant reference has a Brier score of 0.002203889. The logistic model has a slightly lower score of 0.002197249:

$$
\text{Brier skill}
=1-\frac{0.002197249}{0.002203889}
\approx0.003013.
$$

Expressed as a percentage, the model reduces Brier error by only about 0.30% relative to the reference.

### Step 5: Interpret the three results together

The measures tell a clear story:

- **ROC-AUC of 0.7706:** event observations are usually ranked above non-event observations;
- **AP lift of 4.09:** event observations are more concentrated near the top than under the event-share baseline; and
- **Brier skill of 0.003:** the probabilities improve only slightly on the constant past-event-rate prediction.

There is no contradiction. The model can provide useful ranking information without estimating the probability scale much better than the simple reference.

| 2017 tuning result | Value | Meaning |
|---|---:|---|
| Event share | 0.2208% | Events are very rare |
| ROC-AUC | 0.7706 | An event observation outranks a non-event observation about 77.1% of the time |
| Average precision | 0.9033% | Positive observations are more concentrated near the top than under an uninformative ranking |
| AP lift | 4.0904 | Average precision is 4.09 times the event share |
| Reference Brier score | 0.002203889 | Error from assigning every observation the past event rate |
| Model Brier score | 0.002197249 | Logistic model's probability error |
| Brier skill | 0.003013 | Approximately 0.30% less Brier error than the reference |

## 7. Why Class Weighting Shows the Difference Clearly

The balanced logistic candidate in the same 2017 fold has:

- average-precision lift of 3.87;
- model Brier score of approximately 0.2001; and
- Brier skill of -89.77 before calibration.

The model still ranks positive observations better than the event-share baseline. However, its Brier error is approximately 90.77 times the reference error because:

$$
1-(-89.77)=90.77.
$$

Balanced class weights force the model to pay more attention to rare positive observations. This can improve ranking or detection, but the resulting raw probabilities may be much too high. Probability calibration is considered later in the thesis for this reason.

## 8. How the Thesis Uses the Measures

Each candidate setting is evaluated in two expanding yearly folds:

1. fit on 2011–2016 and validate on 2017;
2. add eligible 2017 observations, refit, and validate on 2018.

ROC-AUC is reported for every candidate as a general ranking measure. Candidate settings within each model family are ranked by:

1. highest mean annual average-precision lift;
2. highest mean annual Brier skill when the lift is tied; and
3. fixed candidate order for an exact remaining tie.

ROC-AUC is not part of this tuning order. Average-precision lift receives priority because the event is rare and the top of the risk ranking is especially important. These measures select settings within a model family. They do not select the final family or the final probability correction. Those later decisions use separate 2019 and 2020–2022 periods, as explained in [Chapter 4](../thesis/05_chapter_4.md).

## 9. Common Interpretation Mistakes

- **ROC-AUC is not accuracy.** It measures pairwise ranking, not the share of correct yes-or-no predictions.
- **A high ROC-AUC does not guarantee high precision.** Rare events can still produce many false alerts.
- **AP lift is not accuracy.** It compares average precision with the event share.
- **Average precision is not precision at the final alert threshold.** It summarizes many thresholds.
- **A small Brier score is not enough.** Rare outcomes can make a constant low probability look good.
- **Brier skill depends on its reference.** A value has no clear meaning unless the reference prediction is stated.
- **Good ranking does not guarantee good probabilities.** Ranking and probability measures must both be checked.
- **None of these measures proves lending value.** They do not include credit losses, profit, exposure or the cost of false alerts.

## 10. Implementation and Results

- The calculations are implemented in [`mcf/models/train.py`](../../mcf/models/train.py).
- General metric functions are in [`mcf/models/evaluation.py`](../../mcf/models/evaluation.py).
- Fold-level values are stored in [`tuning_fold_scores.csv`](../../results/run_006_full_statement_enrichment/models/tuning_fold_scores.csv).
- Candidate averages are stored in [`tuning_scores.csv`](../../results/run_006_full_statement_enrichment/models/tuning_scores.csv).
