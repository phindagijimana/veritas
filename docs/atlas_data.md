# Atlas: open data sources for epilepsy and TBI

This document catalogues credible, openly accessible (or controlled-access on
request) data sources relevant to the Atlas Data API. It covers two disease
areas and two primary modalities:

| Disease | Imaging (MRI/CT) | Scalp EEG | Intracranial EEG |
|---------|------------------|-----------|------------------|
| **Epilepsy** | MELD Project (incl. IDEAS), ENIGMA-Epilepsy, OpenNeuro BIDS-Epilepsy releases | CHB-MIT, TUSZ, Siena, Bonn, Bern-Barcelona | IEEG.org Portal, MNI Open iEEG Atlas, Mayo HFO DB |
| **Traumatic Brain Injury (TBI)** | TRACK-TBI / FITBIR, CENTER-TBI, ENIGMA Brain Injury, ABIDE-TBI extensions | LIMBIC-CENC subsets, TBI Model Systems (NIDILRR) | Sparse public — see notes below |

Datasets below are grouped by **disease → modality → dataset**. Each entry lists:

- **Source / host**: who curates the data and where it lives.
- **Modality**: MRI, EEG (scalp), iEEG (intracranial), CT, clinical.
- **Disease scope**: what conditions / cohorts the dataset targets.
- **Access**: open download, free registration, or DUA (data-use agreement).
- **Subjects**: approximate cohort size at time of last public release.
- **Why it matters**: what evaluators typically use it for in clinical-AI work.

> **A note on accuracy.** Cohort sizes and URLs change. Treat all numbers
> below as "approximate, last verified ~2024–2025" and confirm against the
> dataset's own portal before staging into Atlas.

---

## Epilepsy

### Structural / functional MRI

#### MELD Project (and the IDEAS cohort)

- **Source / host**: [meldproject.org](https://meldproject.org) (UCL-led
  multi-centre consortium). Code and trained classifiers via the MELD
  GitHub organisation; raw data hosted at participating sites.
- **Modality**: T1w MRI (and often FLAIR), with expert lesion masks.
- **Disease scope**: Focal Cortical Dysplasia (FCD). Some sub-cohorts
  cover other lesion types and MRI-negative epilepsy.
- **Access**: De-identified harmonised data shared under DUA among MELD
  collaborators. The trained MELD Graph classifier is publicly downloadable
  and is the baseline used in Veritas pipelines.
- **Subjects**: ~600 across 22+ sites in the canonical MELD cohort.
- **Why it matters**: The MELD Graph pipeline shipped with this repo
  (`docker.io/phindagijimana321/meld_graph:v2.2.4-nir2`) was trained against
  this cohort. The **IDEAS** cohort referenced in the Atlas seed
  (`atlas_dataset_id="ideas"`) is the IDEAS sub-study used by MELD.

#### ENIGMA-Epilepsy

- **Source / host**: [enigma.ini.usc.edu/ongoing/enigma-epilepsy](https://enigma.ini.usc.edu/ongoing/enigma-epilepsy/) (USC ENIGMA consortium).
- **Modality**: Harmonised volumetric and DTI features (FreeSurfer parcellations, cortical thickness, subcortical volumes) — not raw images.
- **Disease scope**: Mixed epilepsy syndromes incl. mTLE (mesial temporal lobe), IGE (idiopathic generalised), and JME. Includes left/right TLE-HS sub-cohorts.
- **Access**: Working-group authored, summary-statistic level; raw data stays at sites.
- **Subjects**: 2000+ patients, 1500+ controls across 24+ sites in the original ENIGMA-Epilepsy paper (Whelan et al., 2018).
- **Why it matters**: Reference for normative TLE / HS atrophy patterns and effect sizes when building a leaderboard baseline.

#### OpenNeuro BIDS-Epilepsy releases

- **Source / host**: [openneuro.org](https://openneuro.org/) (Stanford / Squishymedia).
- **Modality**: T1w, T2w, FLAIR, sometimes DTI, fMRI; BIDS-formatted.
- **Disease scope**: Various — search by `ds00…` IDs; e.g. `ds003498` and `ds004027` cover SEEG and surgical-epilepsy cohorts.
- **Access**: Open download or controlled — depends on the dataset's licence.
- **Subjects**: Per-dataset; typically 10–200.
- **Why it matters**: Good for evaluating BIDS-conformance and per-site generalisability of FCD detectors.

#### EPILEPSIAE imaging sub-cohort

- **Source / host**: [epilepsy-database.eu](http://www.epilepsy-database.eu/).
- **Modality**: Primarily long-term EEG (see EEG section); a sub-cohort has co-registered MRI.
- **Disease scope**: Drug-resistant focal epilepsy.
- **Access**: Paid annual licence; DUA required.
- **Subjects**: 275 patients with multi-day EEG; subset has MRI.
- **Why it matters**: Pairs imaging with long EEG monitoring — useful for multimodal pipelines.

### Scalp EEG

#### TUH EEG Corpus & TUSZ (TUH Seizure Corpus)

- **Source / host**: [isip.piconepress.com/projects/tuh_eeg](https://isip.piconepress.com/projects/tuh_eeg/) (Temple University Hospital, Neural Engineering Data Consortium).
- **Modality**: Routine scalp EEG (10–20 system, EDF).
- **Disease scope**: Mixed inpatient population; TUSZ is the **seizure-annotated** subset (`tusz`); TUSL covers status-epilepticus; TUEP epileptiform discharges.
- **Access**: Free registration + signed access agreement.
- **Subjects**: TUH EEG Corpus 25,000+ sessions / 14,000+ patients (full); TUSZ ~5,600 sessions seizure-labelled.
- **Why it matters**: The de facto largest annotated scalp-EEG corpus for seizure detection benchmarks.

#### CHB-MIT Scalp EEG Database

- **Source / host**: [physionet.org/content/chbmit](https://physionet.org/content/chbmit/1.0.0/) (PhysioNet, MIT + Children's Hospital Boston).
- **Modality**: Long-term scalp EEG (23 channels typically, 256 Hz).
- **Disease scope**: Pediatric intractable seizures.
- **Access**: Open download (ODC-By license).
- **Subjects**: 22 pediatric patients, 977+ hours, 198 annotated seizures.
- **Why it matters**: Classic benchmark for seizure-prediction / detection algorithms.

#### Siena Scalp EEG Database

- **Source / host**: [physionet.org/content/siena-scalp-eeg](https://physionet.org/content/siena-scalp-eeg/1.0.0/).
- **Modality**: 29-channel scalp EEG (256 Hz).
- **Disease scope**: Adult drug-resistant focal epilepsy.
- **Access**: Open download (ODC-By license).
- **Subjects**: 14 patients, ~128 hours, 47 seizures.
- **Why it matters**: Smaller but cleaner companion to CHB-MIT for adults.

#### Bonn University EEG Dataset

- **Source / host**: University of Bonn, Department of Epileptology (Andrzejak et al., 2001).
- **Modality**: Single-channel EEG segments (sets A–E).
- **Disease scope**: Interictal, ictal, and healthy comparisons.
- **Access**: Open download.
- **Subjects**: 5 sets × 100 segments × 23.6 s.
- **Why it matters**: Historical baseline used by hundreds of seizure-classification papers — useful for sanity-checking new methods.

#### Bern-Barcelona EEG Database

- **Source / host**: [ntsa.upf.edu](https://ntsa.upf.edu/) (Pompeu Fabra / Bern).
- **Modality**: Focal vs non-focal intracranial EEG signals (despite its name).
- **Disease scope**: Pharmacoresistant epilepsy.
- **Access**: Open download.
- **Subjects**: 5 patients, 7500 channel-pairs.
- **Why it matters**: Standard benchmark for focal-vs-non-focal classification.

### Intracranial EEG (iEEG)

#### IEEG.org Portal

- **Source / host**: [ieeg.org](https://www.ieeg.org/) (Penn + Mayo Clinic, NINDS-funded BRAIN initiative).
- **Modality**: Multi-channel iEEG (SEEG and ECoG), often with imaging co-registration metadata.
- **Disease scope**: Drug-resistant focal epilepsy.
- **Access**: Free researcher registration; per-dataset access.
- **Subjects**: 1500+ recordings across multiple cohorts.
- **Why it matters**: The largest open iEEG portal — used for seizure-onset-zone localisation and HFO detection benchmarks.

#### MNI Open iEEG Atlas (Frauscher Atlas)

- **Source / host**: [mni-open-ieegatlas.research.mcgill.ca](https://mni-open-ieegatlas.research.mcgill.ca/) (Montreal Neurological Institute, McGill).
- **Modality**: SEEG recordings from non-pathological brain regions in epilepsy patients.
- **Disease scope**: Healthy-brain reference from epilepsy patients (i.e. signals outside the seizure-onset zone).
- **Access**: Open download.
- **Subjects**: ~106 patients, 1772 channels, wakeful + sleep.
- **Why it matters**: Normative iEEG atlas for spectral and connectivity baselines.

#### Mayo HFO Open Database

- **Source / host**: Mayo Clinic, via [hfodatabase.dev](https://hfodatabase.dev/) (when active) or IEEG.org mirror.
- **Modality**: High-frequency-oscillation (HFO) annotated iEEG.
- **Disease scope**: Focal epilepsy.
- **Access**: Open with attribution.
- **Subjects**: Tens of patients depending on release.
- **Why it matters**: Gold-standard HFO benchmarks.

### Long-term continuous EEG

#### EPILEPSIAE

- **Source / host**: [epilepsy-database.eu](http://www.epilepsy-database.eu/) (EU FP7 consortium).
- **Modality**: Long-term scalp EEG (some also intracranial); video co-recorded.
- **Disease scope**: Drug-resistant focal epilepsy.
- **Access**: Paid annual licence; DUA required.
- **Subjects**: 275 patients, several days of EEG each.
- **Why it matters**: Largest pre-surgical monitoring corpus with structured annotation; widely used for prediction-horizon studies.

---

## Traumatic Brain Injury (TBI)

### Structural / functional MRI

#### TRACK-TBI (and FITBIR hosting)

- **Source / host**: [tracktbi.ucsf.edu](https://tracktbi.ucsf.edu/) (UCSF-led, NIH-funded). Data deposited in [FITBIR](https://fitbir.nih.gov/).
- **Modality**: 3T MRI (T1, FLAIR, DWI, SWI, fMRI), CT, blood biomarkers, neuropsych, outcomes.
- **Disease scope**: Mild–severe TBI; healthy & orthopaedic controls.
- **Access**: FITBIR DUA + IRB.
- **Subjects**: ~2700 prospectively enrolled across 18 sites in TRACK-TBI Pilot + Phase 1.
- **Why it matters**: Largest multi-site TBI imaging cohort in the US; primary target for AI models predicting outcome from acute imaging.

#### CENTER-TBI

- **Source / host**: [center-tbi.eu](https://www.center-tbi.eu/) (EU multi-site).
- **Modality**: Acute CT (universal), MRI (subset), clinical, biomarkers, outcomes (GOSE).
- **Disease scope**: Adult TBI of all severities; some sub-projects on paediatric TBI.
- **Access**: Application via [the data sharing portal](https://www.center-tbi.eu/data); DUA.
- **Subjects**: ~4500 patients across 22 countries.
- **Why it matters**: European counterpart to TRACK-TBI; harmonised with TRACK-TBI for cross-Atlantic studies.

#### FITBIR (Federal Interagency TBI Research)

- **Source / host**: [fitbir.nih.gov](https://fitbir.nih.gov/) (NIH / NICHD / DOD).
- **Modality**: Heterogeneous — imaging, clinical, biomarkers, omics.
- **Disease scope**: TBI across studies; aggregates TRACK-TBI, CENC/LIMBIC, sports-concussion cohorts, and more.
- **Access**: Free researcher account + DUA per study.
- **Subjects**: Tens of thousands across all member studies.
- **Why it matters**: The single portal where most US-funded TBI data lives; access path for nearly every named TBI study.

#### ENIGMA Brain Injury working group

- **Source / host**: [enigma.ini.usc.edu/ongoing/enigma-brain-injury](https://enigma.ini.usc.edu/ongoing/enigma-brain-injury/).
- **Modality**: Harmonised morphometric and DTI summary statistics across sites.
- **Disease scope**: TBI (sports, military, civilian); chronic moderate–severe TBI.
- **Access**: Working-group governed.
- **Subjects**: 2500+ patients across 30+ cohorts.
- **Why it matters**: Reference for white-matter integrity and atrophy effect sizes in TBI.

#### LIMBIC-CENC (Long-term Impact of Military-Relevant Brain Injury)

- **Source / host**: [limbic-cenc.org](https://limbic-cenc.org/) (DOD/VA, Boston VA Healthcare System).
- **Modality**: 3T MRI, blood biomarkers, neuropsych, longitudinal outcomes.
- **Disease scope**: Service-member / veteran mTBI, blast exposure.
- **Access**: Application via FITBIR.
- **Subjects**: 2700+ longitudinally enrolled.
- **Why it matters**: Most mature open mTBI cohort with longitudinal outcomes.

#### TBI Model Systems (NIDILRR)

- **Source / host**: [tbindsc.org](https://www.tbindsc.org/) (National Data and Statistical Center).
- **Modality**: Clinical, functional outcomes, longitudinal follow-up (predominantly non-imaging).
- **Disease scope**: Moderate–severe TBI requiring inpatient rehabilitation.
- **Access**: Application + DUA.
- **Subjects**: 20,000+ enrolled over 30 years across 16 designated centres.
- **Why it matters**: Reference outcomes (FIM, DRS, GOSE) for longitudinal prediction; sparse imaging but valuable clinical-AI ground truth.

### EEG in TBI

Public TBI-specific EEG corpora are notably sparser than the epilepsy
landscape. Most TBI EEG data is held in clinical EHRs or unreleased
study-specific repositories. Pragmatic sources:

- **CENTER-TBI EEG sub-study** — acute-care continuous EEG in ICU patients; access via the CENTER-TBI data portal (DUA).
- **TUH EEG Corpus** — contains TBI-coded sessions identifiable by ICD code; useful as a heterogeneous, real-world baseline.
- **OpenNeuro** — occasional TBI EEG datasets (search `tbi`); typically small (n<30).
- **PhysioNet EEG datasets** — `eegmmidb` and others are healthy-control baselines that pair well with TBI studies.

If you need TBI EEG specifically for a Veritas pipeline, expect to combine
clinical-site recordings (DUA per site) with these public references rather
than relying on a single open corpus.

---

## Cross-cutting & control datasets (useful for both)

| Dataset | Use | Access |
|---------|-----|--------|
| **Human Connectome Project (HCP)** | Healthy adult MRI / fMRI / DTI baseline; 1200-subject young-adult release | Free registration |
| **IXI dataset** | Healthy MRI baseline (~600 subjects, multi-modal) | Open |
| **OASIS-3 / OASIS-4** | Aging + AD baselines; sometimes used as controls in TBI/epilepsy work | Free registration |
| **ADNI** | Aging + AD; same use as OASIS | Free with DUA |
| **OpenNeuro** | Catch-all BIDS hosting platform — search by condition | Per-dataset |
| **PhysioNet** | EEG / ECG / iEEG hosting platform — search by condition | Per-dataset |

---

## How this maps into Atlas / Veritas

The Atlas Data API exposes each registered dataset under a stable
`atlas_dataset_id`. The seeded datasets at boot-time (see
`veritas/.../backend/app/main.py` and `atlas_api_app/`) map to entries
above:

| Atlas `atlas_dataset_id` | Source above | Modality | Disease |
|-----|------|------|------|
| `ideas` | MELD Project — IDEAS cohort | T1w MRI | Focal Cortical Dysplasia (FCD) |
| `fcd` | MELD Project — FCD cohort | T1w MRI | FCD |
| `hs` | ENIGMA-Epilepsy mTLE-HS sub-cohort or local clinical | T1w MRI | Hippocampal Sclerosis (mTLE) |
| `ad` | ADNI / OASIS | T1w MRI | Alzheimer's Disease |
| `eeg` | TUSZ / CHB-MIT (depending on local mirror) | Scalp EEG | Mixed epilepsy |

### When you add a new dataset

1. Stage the BIDS / EDF tree at the `hpc_root_path` listed in the Atlas
   record, or expose it via Pennsieve and let Atlas resolve it.
2. Add or update the dataset row through the Atlas admin endpoints
   (`POST /api/v1/datasets`) including the `disease_group`,
   `modality`, `subject_count`, and citation URL.
3. If the licence requires per-user DUA, store the agreement reference in
   the dataset's `qc_status` notes; the staging request flow in Atlas
   already gates downloads behind admin approval.

### When in doubt

Cite the **original paper** for the cohort plus the **portal URL**. The
Atlas audit log records who requested what; if a dataset later requires
take-down, every download is traceable.
