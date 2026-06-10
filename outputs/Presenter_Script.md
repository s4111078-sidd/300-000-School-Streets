# Presenter Script — School Streets Safety Analysis
**Regen Melbourne × RMIT University | City of Darebin Pilot**
Estimated duration: 12–15 minutes | 11 slides

Audience: Data science, social science, one Vic Health representative
Tone: Evidence-based, accessible, policy-facing

---

## SLIDE 1 — Title (~1 min)

*Open with the slide visible. Let the stat cards land before speaking.*

> "Good [morning/afternoon]. I'm going to talk today about school streets —
> specifically, what happens when children walk to school in Melbourne, whether
> those streets are safe, and whether the communities that rely on them the most
> are being served or failed by them.
>
> We're Regen Melbourne working with RMIT University. This project is called
> 300,000 Streets of Melbourne — the number of street segments across the city
> that we ultimately want to assess. Today we'll show you a proof-of-concept
> focused on three secondary schools in Darebin.
>
> Before I go further — the number on the right there, 192%, is the increase in
> pedestrian and cyclist crashes in Darebin between 2021 and 2024. And 17:00 is
> the peak crash hour. That's school pickup time. That context drives everything
> we did."

**Key numbers to reference verbally:**
- 3 schools, 7,948 crashes analysed
- 192% crash increase
- r = 0.84 equity correlation
- 17:00 peak hour

**For Vic Health:** Emphasise that active travel is the entry point — this is a
physical activity, air quality, and mental health story as much as a road safety one.

---

## SLIDE 2 — The Problem (~2 min)

*Point to the three left panels in sequence.*

> "Let me be concrete about the problem. Darebin LGA had 25 pedestrian and
> cyclist crashes in 2021. By 2024 that number was 73. Nearly three times as
> many. And when we look at the timing, the single most dangerous hour of the
> day is 5pm — that's not commuters, that's children being picked up from
> school, or walking home.
>
> Preston High School has 15 crashes recorded within 400 metres of its main
> gate across four years. That's not a statistical abstraction — that's a crash
> outside the school once every three months, on average.
>
> And William Ruthven Secondary College: 100% of the crashes we recorded near
> its gate happened during school hours.
>
> The equity number, r = 0.84, I'll explain in detail later — but the short
> version is: the most disadvantaged communities in Darebin have the worst
> streets. That's the core finding."

**For social science audience:** Broaden the framing — streets as social
infrastructure, not just transport infrastructure. The question is: who bears
the risk when investment decisions are made?

**For Vic Health:** Active travel to school is associated with better physical
fitness, mental health, and lifelong activity habits. Dangerous streets don't
just cause crashes — they cause parents to drive children, which removes the
active travel benefit entirely.

---

## SLIDE 3 — How We Approached It (~1.5 min)

*Left column: Healthy Streets framework. Right column: the pipeline.*

> "We grounded this in the Healthy Streets framework — developed by Lucy Saunders
> for Transport for London and now used in cities worldwide. It gives us ten
> indicators, each scored zero to ten, that describe the human experience of a
> street. Not just whether a road is wide enough for cars, but whether there's
> shade, whether you feel safe, whether crossing the road is possible.
>
> On the right you can see our ten-step pipeline. We combined field observation
> data collected at each school gate with open government data — VicRoads crash
> records, OpenStreetMap spatial data, EPA air quality, Crime Statistics Agency
> Victoria, and ABS Census and SEIFA data.
>
> Everything is automated and reproducible. Adding a new school takes minutes.
> The full pipeline reruns from source data with one command."

**For data science audience:** Note that step 6 (Ridge regression) uses
Leave-One-Out cross-validation because n=3. The model is trained on all schools
and predicts each one held-out in turn. This is the methodologically correct
choice for very small samples.

**Transition:** "Let's see what those scores actually looked like."

---

## SLIDE 4 — Safety Scores (~2 min)

*Point to the three flag annotations, then walk through each panel.*

> "Each panel here shows one school's ten indicator scores. Green bars are at or
> above the 6.0 standard threshold. Amber is below standard. Red is critical.
>
> The most urgent case is Preston High School — that's the left panel.
> See that second bar? That's HS2 — Easy to Cross. It scores 0.4 out of 10.
> The reason is simple: there is no formal pedestrian crossing adjacent to the
> school gate. Children are crossing an arterial road informally. That's a
> Major hazard classification, and it's the kind of thing that is both
> very dangerous and relatively cheap to fix.
>
> Reservoir High School, in the middle, has five indicators below standard —
> footpath, crossing, shade, noise, and feeling relaxed. Five separate failure
> modes on a single school route.
>
> William Ruthven has the lowest shade and shelter score of all three schools —
> HS3 of 3.0. There is almost no tree canopy on the walking routes near
> this school."

**For Vic Health:** The HS3 (shade/shelter) and HS5 (noise) indicators map
directly to UV exposure, respiratory health, and psychological stress. A score
of 3.0 for shade means children are walking to school in full sun with no cover.

---

## SLIDE 5 — Crash Trends (~2 min)

*Reference the four stat cards on the left, then the chart panels.*

> "Let me now show you the crash data behind those scores.
>
> The top-left panel shows Darebin LGA crashes by year. The trend is
> unmistakeable — 25 in 2021, 53 in 2022, 59 in 2023, 73 in 2024. That's not
> noise. Something structural is happening. We don't yet know if it's increased
> walking post-COVID, worse street conditions, underreporting in earlier years,
> or some combination.
>
> Bottom right is the time-of-day distribution. See that spike at 17:00?
> That's the school pickup window. The number of crashes during that one-hour
> window is higher than any other single hour of the day.
>
> For our three specific schools: Preston HS has 15 crashes near its gate.
> 100% of William Ruthven SC's nearby crashes occurred during school hours —
> which makes sense, because the gate opens onto a busy road and there is no
> crossing."

**For data science audience:** The statewide dataset has 7,948 crashes. We
filtered to Darebin LGA using a 400m gate buffer via vectorised haversine
distance. Nearest-school assignment is also haversine-based, not
Voronoi-based, which is more appropriate for sparse gate points.

---

## SLIDE 6 — Equity (~2 min)

*Hold on the r = 0.84 callout first, then move to the chart.*

> "This is the finding that I think matters most from a policy perspective.
>
> That correlation coefficient — 0.84 — is between SEIFA disadvantage decile
> and Healthy Streets overall score. SEIFA is the Australian Bureau of Statistics
> index of relative socioeconomic disadvantage. A higher decile means less
> disadvantaged.
>
> What this says is: schools in more disadvantaged areas have worse pedestrian
> safety. Reservoir High School is in SEIFA Decile 3.7 — one of the most
> disadvantaged catchments in Darebin. It also has the lowest HS score of our
> three schools, 6.1 out of 10.
>
> Preston High School is in a moderately disadvantaged area — Decile 5.5 —
> and its score is 7.2. Higher score, less disadvantaged.
>
> Now, n=3, so we're careful not to overclaim causality. But this directional
> finding is consistent with evidence from Transport for London and WHO active
> travel research. Disadvantage and dangerous streets co-occur. And when you
> look at the scatter plot on the right, you can see exactly where each school
> sits relative to the 'at-risk' quadrant — low decile, low HS score.
>
> The implication for investment is clear: a needs-based, equity-weighted
> prioritisation framework should put Reservoir at the top of the list."

**For Vic Health:** Car ownership in these catchments is 11–12% below
Melbourne median. Families without cars depend on walking and transit.
Dangerous streets don't just injure — they restrict access to education,
healthcare, and employment. That is a health equity issue.

---

## SLIDE 7 — Machine Learning (~1.5 min)

> "A natural question is: do we need to send people out to every school with
> clipboards? Or can we estimate these scores from open data?
>
> We trained a Ridge regression model — appropriate for small samples, it
> regularises heavily — on 26 open-data features, and evaluated it using
> leave-one-out cross-validation.
>
> The left table shows three tiers of result. Some indicators we can fully
> automate: HS7, safety, has a mean absolute error of just 0.54 — because crime
> statistics are a reliable proxy. HS10, air quality, is 0.92 because EPA's
> AQI maps directly onto the indicator.
>
> But look at HS2 — Easy to Cross — MAE of 4.51. The model can detect whether
> a crossing is present from OpenStreetMap. But it cannot detect whether that
> crossing is usable, well-lit, tactile-paved, or at the right distance from
> the gate. Presence is not quality. HS2 requires field observation at any
> sample size.
>
> The chart on the right shows predicted versus actual. See the Preston HS HS2
> bar — actual is 0.4, predicted is 3.2. The model has never seen a score that
> low, so it can't predict it. That's exactly why ground-truthing matters."

**For data science audience:** n=3 means the LOO-CV results are illustrative
and not generalisable. With 20+ schools, the model's utility for rapid
screening would be much stronger. The purpose here is to demonstrate the
methodology, not claim production-ready accuracy.

---

## SLIDE 8 — What Can Be Done (~1.5 min)

> "Given these scores, what can we actually do?
>
> We built a scenario engine. You can pick a physical intervention — say,
> install a signalised pedestrian crossing, or reduce the speed limit to 40
> km/h, or plant street trees — and the model tells you how much each HS
> indicator would change.
>
> The chart on the right shows Preston HS with two interventions applied:
> a pedestrian crossing and a 40 km/h school zone. Most indicators improve
> slightly. HS1 — footpath — improves by 0.37 because the intervention
> features include walking network improvements.
>
> One note on the HS2 delta: the Ridge model predicts a slight negative change
> for HS2. This is a known artefact with n=3 — the model was trained on only
> two schools when predicting Preston, and the feature coefficients don't
> generalise well to an extreme score like 0.4. In practice, installing a
> crossing would unambiguously improve HS2. We flag this as a model limitation,
> not a physical reality.
>
> On the left you can see the 10 interventions with indicative costs and
> lead times. A speed limit reduction costs $5–20k and can be done in under
> six months. A signalised crossing is $80–200k and under a year. These are
> decisions councils can make with existing budgets."

---

## SLIDE 9 — Recommendations (~2 min)

*Walk through each column.*

> "Based on the Healthy Streets scores, crash data, and equity analysis, here
> are our prioritised recommendations for each school.
>
> Preston High School — Major severity — the single most urgent action is
> installing a signalised crossing at the school gate. Not a painted crossing.
> A signalised crossing with tactile pavers, good sightlines, and proper
> timing. HS2 = 0.4 means this is a critical safety gap. Cost: $80–200k.
> Timeframe: under a year if approvals move quickly.
>
> Reservoir High School — Moderate severity with five indicators below standard
> — the priority is continuous footpath on Plenty Road. There are sections
> missing, which forces pedestrians onto the road. HS1 = 4.2. Cost: $100–300k.
>
> William Ruthven Secondary College — the shadow and shelter deficit is severe.
> HS3 = 3.0 is the lowest of any indicator at any school. Street trees take
> time to grow but planting can start immediately. Cost: $35–100k.
>
> All 17 recommendations with indicator, cost and timeframe are available in
> the filterable table on the project dashboard."

---

## SLIDE 10 — Interactive Dashboard (~1 min)

> "Everything we've shown today — all the scores, charts, crash data, scenario
> analysis, and recommendations — is available in an interactive web dashboard.
>
> It runs entirely in the browser, no installation required. It's hosted on
> GitHub Pages. You can filter recommendations by school and priority, run
> what-if scenarios by selecting an intervention, and explore the Leaflet map
> where each school marker is colour-coded by severity — red pulse for Major.
>
> I'd encourage you to explore it after this presentation. It's the kind of
> tool a council planner, a community advocate, or a Vic Health officer could
> use to make the case for specific investments at specific schools."

**Live demo option:** If time permits, open the dashboard and click through
the School Assessments tab for Preston HS and the Scenario Explorer.

---

## SLIDE 11 — Scale-Up & Next Steps (~1 min)

> "We've shown a proof of concept across three schools. The same pipeline runs
> on any school gate in Victoria. Victoria has roughly 1,900 government schools.
> The data sources we used are all publicly available and statewide.
>
> The three things we need to scale this are: more schools to improve the ML
> model's accuracy, partnerships with Vic Health, DET, or VicRoads to use the
> equity lens for triage — which schools do we assess first? — and longitudinal
> data to validate whether predicted improvements match actual crash reductions
> after interventions are built.
>
> The vision is simple: every child should be able to walk to school safely.
> We now have a tool that can identify where that's not happening, how bad it
> is, and what it would cost to fix it. The next step is to use it."

**Closing line:**
> "Thank you. Happy to take questions on the data, the methodology, the equity
> findings, or what a partnership to scale this might look like."

---

## Q&A Preparation

**Likely questions and suggested answers:**

**"How reliable is the r = 0.84 equity correlation with only 3 schools?"**
> It's a directional finding, not a definitive claim. With n=3, Pearson r is
> highly sensitive to individual data points. The finding is consistent with
> the broader literature on transport inequity, but we need 15–20 schools
> across multiple LGAs to make a statistically robust claim.

**"Why Ridge regression and not something more powerful?"**
> With n=3, any complex model will overfit perfectly. Ridge regression with
> L2 regularisation is the appropriate choice — it's interpretable, stable,
> and the regularisation parameter prevents the model from memorising the
> training data. With more schools we'd evaluate Gradient Boosting or
> Gaussian Processes.

**"Have you validated the HS field scores against independent observers?"**
> Not yet — inter-rater reliability testing is on the roadmap. The Healthy
> Streets framework has been validated in TfL's London deployment, but our
> local application would benefit from a second observer assessing each gate
> independently.

**"What would it take to implement the Preston HS crossing?"**
> It would need a referral to the City of Darebin traffic engineering team,
> a road safety audit, and VicRoads approval for the arterial crossing. A
> school safety review submitted through the DET school safety program could
> expedite this. The $80–200k estimate is from VicRoads' published crossing
> installation benchmarks.

**"Can this tool be used by individual schools or community groups?"**
> Yes — the dashboard is publicly accessible and requires no technical
> knowledge. The scenario explorer is designed to be usable by a school
> council member or community advocate to make the case for a specific
> intervention to their local council.

---

*Script prepared: June 2026 | Regen Melbourne × RMIT University*
