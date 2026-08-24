# Data Model — Discovered Resource Types and Codes

> Generated empirically by `python -m previsit.ingest.inspect_output` from the actual FHIR bundles in `data/synthea_output/fhir`. Nothing below is hardcoded from memory or from SPEC.md — every code and count reflects what this run of Synthea actually produced.

**Patient-level bundles:** 1175

## Notes for implementers

- **Bundle count vs. population target:** `-p 1000` targets 1000 *living* patients at simulation end, not 1000 total bundles. Synthea also generates deceased patients along the way for demographic realism and keeps them in the output — this run produced 1000 living + 175 deceased = 1175 patient bundles. Kept intentionally: Phase 3's care-gap rules must exclude deceased patients, so real deceased records let that exclusion be tested for real.
- **The clinical code field is not uniformly `.code` across resource types.** Verified against actual output, not assumed: `Immunization` uses `.vaccineCode`, `MedicationRequest` uses `.medicationCodeableConcept`, `CarePlan` has no top-level `.code` at all (uses `.category`), and `Encounter.class` is a bare `Coding`, not a `CodeableConcept` (so it has no `.coding[]` array — pull `system`/`code`/`display` directly off it).
- **FHIR version confirmed R4** empirically from the jar's bundled `synthea.properties` (`exporter.fhir_stu3.export = false`, `exporter.fhir_dstu2.export = false`), matching the spec requirement — not assumed.

## Resource type counts

| Resource type | Count |
|---|---|
| Observation | 700516 |
| Procedure | 207232 |
| DiagnosticReport | 152112 |
| Claim | 141208 |
| ExplanationOfBenefit | 141208 |
| Encounter | 73448 |
| DocumentReference | 73448 |
| MedicationRequest | 67760 |
| Condition | 45514 |
| SupplyDelivery | 31282 |
| Medication | 25192 |
| MedicationAdministration | 25192 |
| Immunization | 16818 |
| Device | 7142 |
| ImagingStudy | 6548 |
| CareTeam | 4006 |
| CarePlan | 4006 |
| Patient | 1175 |
| Provenance | 1175 |
| AllergyIntolerance | 1150 |
| Location | 912 |
| Organization | 911 |
| Practitioner | 911 |
| PractitionerRole | 911 |

## Codes observed per resource type

Every distinct `(system, code, display)` triple actually present, sorted by frequency. These are Synthea's synthetic code sets, not guaranteed identical across Synthea versions — this is why the engine (Phase 3) looks codes up empirically rather than assuming them.

### Encounter (58 distinct codes)

| Count | System | Code | Display |
|---|---|---|---|
| 68304 | http://terminology.hl7.org/CodeSystem/v3-ActCode | AMB | (no display) |
| 19668 | http://snomed.info/sct | 185347001 | Encounter for problem (procedure) |
| 12506 | http://snomed.info/sct | 185349003 | Encounter for check up (procedure) |
| 10784 | http://snomed.info/sct | 162673000 | General examination of patient (procedure) |
| 3986 | http://snomed.info/sct | 702927004 | Urgent care clinic (environment) |
| 3867 | http://snomed.info/sct | 185345009 | Encounter for symptom (procedure) |
| 3555 | http://snomed.info/sct | 410620009 | Well child visit (procedure) |
| 2899 | http://terminology.hl7.org/CodeSystem/v3-ActCode | EMER | (no display) |
| 2550 | http://snomed.info/sct | 424619006 | Prenatal visit (regime/therapy) |
| 2279 | http://snomed.info/sct | 50849002 | Emergency room admission (procedure) |
| 1866 | http://snomed.info/sct | 308335008 | Patient encounter procedure (procedure) |
| 1841 | http://snomed.info/sct | 371883000 | Outpatient procedure (procedure) |
| 1772 | http://snomed.info/sct | 390906007 | Follow-up encounter (procedure) |
| 1484 | http://terminology.hl7.org/CodeSystem/v3-ActCode | IMP | (no display) |
| 1334 | http://snomed.info/sct | 33879002 | Administration of vaccine to produce active immunity (procedure) |
| 1211 | http://snomed.info/sct | 698314001 | Consultation for treatment (procedure) |
| 1069 | http://snomed.info/sct | 36228007 | Ophthalmic examination and evaluation (procedure) |
| 864 | http://snomed.info/sct | 448337001 | Telemedicine consultation with patient (procedure) |
| 609 | http://terminology.hl7.org/CodeSystem/v3-ActCode | HH | (no display) |
| 466 | http://snomed.info/sct | 424441002 | Prenatal initial visit (regime/therapy) |
| 425 | http://snomed.info/sct | 439708006 | Home visit (procedure) |
| 397 | http://snomed.info/sct | 439740005 | Postoperative follow-up visit (procedure) |
| 331 | http://snomed.info/sct | 32485007 | Hospital admission (procedure) |
| 323 | http://snomed.info/sct | 394701000 | Asthma follow-up (regime/therapy) |
| 270 | http://snomed.info/sct | 169762003 | Postnatal visit (regime/therapy) |
| 269 | http://snomed.info/sct | 183460006 | Obstetric emergency hospital admission (procedure) |
| 209 | http://snomed.info/sct | 56876005 | Drug rehabilitation and detoxification (regime/therapy) |
| 184 | http://snomed.info/sct | 305336008 | Admission to hospice (procedure) |
| 168 | http://snomed.info/sct | 308646001 | Death Certification |
| 152 | http://terminology.hl7.org/CodeSystem/v3-ActCode | VR | (no display) |
| 151 | http://snomed.info/sct | 410410006 | Screening surveillance (regime/therapy) |
| 133 | http://snomed.info/sct | 305408004 | Admission to surgical department (procedure) |
| 128 | http://snomed.info/sct | 183452005 | Emergency hospital admission (procedure) |
| 109 | http://snomed.info/sct | 310061009 | Gynecology service (qualifier value) |
| 82 | http://snomed.info/sct | 270427003 | Patient-initiated encounter (procedure) |
| 72 | http://snomed.info/sct | 305351004 | Admission to intensive care unit (procedure) |
| 66 | http://snomed.info/sct | 305342007 | Admission to ward (procedure) |
| 62 | http://snomed.info/sct | 281036007 | Follow-up consultation (procedure) |
| 56 | http://snomed.info/sct | 210098006 | Domiciliary or rest home patient evaluation and management (procedure) |
| 55 | http://snomed.info/sct | 170837001 | Allergic disorder initial assessment (regime/therapy) |
| 54 | http://snomed.info/sct | 397821002 | Patient transfer to intensive care unit (procedure) |
| 54 | http://snomed.info/sct | 183478001 | Emergency hospital admission for asthma (procedure) |
| 48 | http://snomed.info/sct | 305432006 | Admission to surgical transplant department (procedure) |
| 35 | http://snomed.info/sct | 170838006 | Allergic disorder follow-up assessment (regime/therapy) |
| 30 | http://snomed.info/sct | 185389009 | Follow-up visit (procedure) |
| 25 | http://snomed.info/sct | 185317003 | Telephone encounter (procedure) |
| 22 | http://snomed.info/sct | 183495009 | Non-urgent orthopedic admission (procedure) |
| 12 | http://snomed.info/sct | 453131000124105 | Videotelephony encounter (procedure) |
| 10 | http://snomed.info/sct | 305411003 | Admission to thoracic surgery department (procedure) |
| 9 | http://snomed.info/sct | 1505002 | Hospital admission for isolation (procedure) |
| 9 | http://snomed.info/sct | 47505003 | Posttraumatic stress disorder (disorder) |
| 7 | http://snomed.info/sct | 86013001 | Periodic reevaluation and management of healthy individual (procedure) |
| 6 | http://snomed.info/sct | 79094001 | Initial psychiatric interview with mental status and evaluation (procedure) |
| 6 | http://snomed.info/sct | 223484005 | Discussion about treatment (procedure) |
| 5 | http://snomed.info/sct | 308251003 | Admission to clinical oncology department (procedure) |
| 4 | http://snomed.info/sct | 4525004 | Emergency department patient visit (procedure) |
| 3 | http://snomed.info/sct | 386395000 | Preoperative coordination (regime/therapy) |
| 1 | http://snomed.info/sct | 108219001 | Physician visit with evaluation AND/OR management service (procedure) |

### Condition (257 distinct codes)

| Count | System | Code | Display |
|---|---|---|---|
| 9180 | http://snomed.info/sct | 314529007 | Medication review due (situation) |
| 3622 | http://snomed.info/sct | 73595000 | Stress (finding) |
| 3360 | http://snomed.info/sct | 66383009 | Gingivitis (disorder) |
| 3337 | http://snomed.info/sct | 160903007 | Full-time employment (finding) |
| 2010 | http://snomed.info/sct | 160904001 | Part-time employment (finding) |
| 1353 | http://snomed.info/sct | 422650009 | Social isolation (finding) |
| 1259 | http://snomed.info/sct | 423315002 | Limited social contact (finding) |
| 1239 | http://snomed.info/sct | 444814009 | Viral sinusitis (disorder) |
| 1174 | http://snomed.info/sct | 741062008 | Not in labor force (finding) |
| 1021 | http://snomed.info/sct | 18718003 | Gingival disease (disorder) |
| 869 | http://snomed.info/sct | 706893006 | Victim of intimate partner abuse (finding) |
| 750 | http://snomed.info/sct | 109570002 | Primary dental caries (disorder) |
| 690 | http://snomed.info/sct | 424393004 | Reports of violence in the environment (finding) |
| 650 | http://snomed.info/sct | 195662009 | Acute viral pharyngitis (disorder) |
| 596 | http://snomed.info/sct | 162864005 | Body mass index 30+ - obesity (finding) |
| 580 | http://snomed.info/sct | 73438004 | Unemployed (finding) |
| 567 | http://snomed.info/sct | 10509002 | Acute bronchitis (disorder) |
| 520 | http://snomed.info/sct | 224299000 | Received higher education (finding) |
| 475 | http://snomed.info/sct | 714628002 | Prediabetes (finding) |
| 453 | http://snomed.info/sct | 72892002 | Normal pregnancy (finding) |
| 451 | http://snomed.info/sct | 271737000 | Anemia (disorder) |
| 296 | http://snomed.info/sct | 160968000 | Risk activity involvement (finding) |
| 287 | http://snomed.info/sct | 82423001 | Chronic pain (finding) |
| 272 | http://snomed.info/sct | 473461003 | Educated to high school level (finding) |
| 270 | http://snomed.info/sct | 266948004 | Has a criminal record (finding) |
| 262 | http://snomed.info/sct | 40055000 | Chronic sinusitis (disorder) |
| 260 | http://snomed.info/sct | 59621000 | Essential hypertension (disorder) |
| 231 | http://snomed.info/sct | 1149222004 | Overdose (disorder) |
| 215 | http://snomed.info/sct | 427898007 | Infection of tooth (disorder) |
| 212 | http://snomed.info/sct | 161744009 | Past pregnancy history of miscarriage (situation) |
| 203 | http://snomed.info/sct | 414545008 | Ischemic heart disease (disorder) |
| 203 | http://snomed.info/sct | 274531002 | Abnormal findings diagnostic imaging heart+coronary circulat (finding) |
| 201 | http://snomed.info/sct | 237602007 | Metabolic syndrome X (disorder) |
| 201 | http://snomed.info/sct | 278860009 | Chronic low back pain (finding) |
| 188 | http://snomed.info/sct | 10939881000119105 | Unhealthy alcohol drinking behavior (finding) |
| 179 | http://snomed.info/sct | 125605004 | Fracture of bone (disorder) |
| 176 | http://snomed.info/sct | 278588009 | Fractured dental filling (finding) |
| 172 | http://snomed.info/sct | 43878008 | Streptococcal sore throat (disorder) |
| 170 | http://snomed.info/sct | 278598003 | Leaking dental filling (finding) |
| 167 | http://snomed.info/sct | 384709000 | Sprain (morphologic abnormality) |
| 163 | http://snomed.info/sct | 312608009 | Laceration - injury (disorder) |
| 163 | http://snomed.info/sct | 278558000 | Dental filling lost (finding) |
| 158 | http://snomed.info/sct | 224295006 | Only received primary school education (finding) |
| 155 | http://snomed.info/sct | 65363002 | Otitis media (disorder) |
| 152 | http://snomed.info/sct | 80583007 | Severe anxiety (panic) (finding) |
| 151 | http://snomed.info/sct | 37320007 | Loss of teeth (disorder) |
| 150 | http://snomed.info/sct | 278602001 | Loose dental filling (finding) |
| 134 | http://snomed.info/sct | 127013003 | Disorder of kidney due to diabetes mellitus (disorder) |
| 133 | http://snomed.info/sct | 307426000 | Acute infective cystitis (disorder) |
| 128 | http://snomed.info/sct | 55822004 | Hyperlipidemia (disorder) |
| 126 | http://snomed.info/sct | 431855005 | Chronic kidney disease stage 1 (disorder) |
| 125 | http://snomed.info/sct | 105531004 | Housing unsatisfactory (finding) |
| 123 | http://snomed.info/sct | 267020005 | History of tubal ligation (situation) |
| 122 | http://snomed.info/sct | 1121000119107 | Chronic neck pain (finding) |
| 118 | http://snomed.info/sct | 446654005 | Refugee (person) |
| 117 | http://snomed.info/sct | 68496003 | Polyp of colon (disorder) |
| 112 | http://snomed.info/sct | 44465007 | Sprain of ankle (disorder) |
| 110 | http://snomed.info/sct | 302870006 | Hypertriglyceridemia (disorder) |
| 109 | http://snomed.info/sct | 44054006 | Diabetes mellitus type 2 (disorder) |
| 107 | http://snomed.info/sct | 90781000119102 | Microalbuminuria due to type 2 diabetes mellitus (disorder) |
| 101 | http://snomed.info/sct | 431856006 | Chronic kidney disease stage 2 (disorder) |
| 101 | http://snomed.info/sct | 840544004 | Suspected disease caused by Severe acute respiratory coronavirus 2 (situation) |
| 95 | http://snomed.info/sct | 840539006 | Disease caused by severe acute respiratory syndrome coronavirus 2 (disorder) |
| 91 | http://snomed.info/sct | 386661006 | Fever (finding) |
| 90 | http://snomed.info/sct | 399261000 | History of coronary artery bypass grafting (situation) |
| 90 | http://snomed.info/sct | 361055000 | Misuses drugs (finding) |
| 79 | http://snomed.info/sct | 110030002 | Concussion injury of brain (disorder) |
| 78 | http://snomed.info/sct | 124171000119105 | Chronic intractable migraine without aura (disorder) |
| 76 | http://snomed.info/sct | 157141000119108 | Proteinuria due to type 2 diabetes mellitus (disorder) |
| 75 | http://snomed.info/sct | 6525002 | Dependent drug abuse (disorder) |
| 74 | http://snomed.info/sct | 196416002 | Impacted molars (disorder) |
| 72 | http://snomed.info/sct | 19169002 | Miscarriage in first trimester (disorder) |
| 70 | http://snomed.info/sct | 49727002 | Cough (finding) |
| 69 | http://snomed.info/sct | 239873007 | Osteoarthritis of knee (disorder) |
| 69 | http://snomed.info/sct | 433144002 | Chronic kidney disease stage 3 (disorder) |
| 66 | http://snomed.info/sct | 75498004 | Acute bacterial sinusitis (disorder) |
| 62 | http://snomed.info/sct | 36971009 | Sinusitis (disorder) |
| 61 | http://snomed.info/sct | 80394007 | Hyperglycemia (disorder) |
| 61 | http://snomed.info/sct | 62106007 | Concussion with no loss of consciousness (disorder) |
| 61 | http://snomed.info/sct | 48333001 | Burn injury (morphologic abnormality) |
| 60 | http://snomed.info/sct | 90460009 | Injury of neck (disorder) |
| 60 | http://snomed.info/sct | 39848009 | Whiplash injury to neck (disorder) |
| 59 | http://snomed.info/sct | 128613002 | Seizure disorder (disorder) |
| 59 | http://snomed.info/sct | 1290882004 | History of seizure (situation) |
| 55 | http://snomed.info/sct | 70704007 | Sprain of wrist (disorder) |
| 53 | http://snomed.info/sct | 39898005 | Sleep disorder (disorder) |
| 53 | http://snomed.info/sct | 428251008 | History of appendectomy (situation) |
| 52 | http://snomed.info/sct | 64859006 | Osteoporosis (disorder) |
| 52 | http://snomed.info/sct | 36955009 | Loss of taste (finding) |
| 52 | http://snomed.info/sct | 266934004 | Transport problem (finding) |
| 51 | http://snomed.info/sct | 713458007 | Lack of access to transportation (finding) |
| 49 | http://snomed.info/sct | 197927001 | Recurrent urinary tract infection (disorder) |
| 47 | http://snomed.info/sct | 61804006 | Alveolitis of jaw (disorder) |
| 46 | http://snomed.info/sct | 195967001 | Asthma (disorder) |
| 45 | http://snomed.info/sct | 698306007 | Awaiting transplantation of kidney (situation) |
| 44 | http://snomed.info/sct | 399211009 | History of myocardial infarction (situation) |
| 44 | http://snomed.info/sct | 78275009 | Obstructive sleep apnea syndrome (disorder) |
| 43 | http://snomed.info/sct | 65966004 | Fracture of forearm (disorder) |
| 43 | http://snomed.info/sct | 84229001 | Fatigue (finding) |
| 42 | http://snomed.info/sct | 431857002 | Chronic kidney disease stage 4 (disorder) |
| 41 | http://snomed.info/sct | 161665007 | History of renal transplant (situation) |
| 41 | http://snomed.info/sct | 156073000 | Complete miscarriage (disorder) |
| 38 | http://snomed.info/sct | 283385000 | Laceration of thigh (disorder) |
| 38 | http://snomed.info/sct | 1551000119108 | Nonproliferative diabetic retinopathy due to type II diabetes mellitus |
| 38 | http://snomed.info/sct | 1187604002 | Serving in military service (finding) |
| 38 | http://snomed.info/sct | 16114001 | Fracture of ankle (disorder) |
| 37 | http://snomed.info/sct | 201834006 | Localized, primary osteoarthritis of the hand (disorder) |
| 36 | http://snomed.info/sct | 403190006 | Epidermal burn of skin (disorder) |
| 35 | http://snomed.info/sct | 91302008 | Sepsis (disorder) |
| 35 | http://snomed.info/sct | 284551006 | Laceration of foot (disorder) |
| 34 | http://snomed.info/sct | 58150001 | Fracture of clavicle (disorder) |
| 34 | http://snomed.info/sct | 88805009 | Chronic congestive heart failure (disorder) |
| 34 | http://snomed.info/sct | 284549007 | Laceration of hand (disorder) |
| 33 | http://snomed.info/sct | 24079001 | Atopic dermatitis (disorder) |
| 32 | http://snomed.info/sct | 263102004 | Fracture subluxation of wrist (disorder) |
| 32 | http://snomed.info/sct | 446096008 | Perennial allergic rhinitis (disorder) |
| 31 | http://snomed.info/sct | 233678006 | Childhood asthma (disorder) |
| 31 | http://snomed.info/sct | 398254007 | Pre-eclampsia (disorder) |
| 29 | http://snomed.info/sct | 84757009 | Epilepsy (disorder) |
| 29 | http://snomed.info/sct | 368581000119106 | Neuropathy due to type 2 diabetes mellitus (disorder) |
| 29 | http://snomed.info/sct | 26929004 | Alzheimer's disease (disorder) |
| 29 | http://snomed.info/sct | 283371005 | Laceration of forearm (disorder) |
| 29 | http://snomed.info/sct | 87433001 | Pulmonary emphysema (disorder) |
| 28 | http://snomed.info/sct | 22298006 | Myocardial infarction (disorder) |
| 28 | http://snomed.info/sct | 183996000 | Sterilization requested (situation) |
| 27 | http://snomed.info/sct | 203082005 | Fibromyalgia (disorder) |
| 27 | http://snomed.info/sct | 370247008 | Facial laceration (disorder) |
| 27 | http://snomed.info/sct | 248595008 | Sputum finding (finding) |
| 27 | http://snomed.info/sct | 713197008 | Recurrent rectal polyp (disorder) |
| 27 | http://snomed.info/sct | 203646004 | Adolescent idiopathic scoliosis (disorder) |
| 27 | http://snomed.info/sct | 125601008 | Injury of knee (disorder) |
| 25 | http://snomed.info/sct | 401303003 | Acute ST segment elevation myocardial infarction (disorder) |
| 25 | http://snomed.info/sct | 241929008 | Acute allergic reaction (disorder) |
| 24 | http://snomed.info/sct | 198992004 | Eclampsia in pregnancy (disorder) |
| 23 | http://snomed.info/sct | 403191005 | Partial thickness burn (disorder) |
| 21 | http://snomed.info/sct | 35999006 | Blighted ovum (disorder) |
| 21 | http://snomed.info/sct | 33737001 | Fracture of rib (disorder) |
| 21 | http://snomed.info/sct | 46177005 | End-stage renal disease (disorder) |
| 20 | http://snomed.info/sct | 1255252008 | Resorption of alveolar process due to dental trauma (disorder) |
| 20 | http://snomed.info/sct | 254837009 | Malignant neoplasm of breast (disorder) |
| 19 | http://snomed.info/sct | 443165006 | Osteoporotic fracture of bone (disorder) |
| 18 | http://snomed.info/sct | 267102003 | Sore throat (finding) |
| 17 | http://snomed.info/sct | 192127007 | Child attention deficit disorder (disorder) |
| 17 | http://snomed.info/sct | 401314000 | Acute non-ST segment elevation myocardial infarction (disorder) |
| 17 | http://snomed.info/sct | 46752004 | Torus palatinus (disorder) |
| 17 | http://snomed.info/sct | 32911000 | Homeless (finding) |
| 16 | http://snomed.info/sct | 267036007 | Dyspnea (finding) |
| 16 | http://snomed.info/sct | 56018004 | Wheezing (finding) |
| 16 | http://snomed.info/sct | 367498001 | Seasonal allergic rhinitis (disorder) |
| 16 | http://snomed.info/sct | 232353008 | Perennial allergic rhinitis with seasonal variation (disorder) |
| 15 | http://snomed.info/sct | 185086009 | Chronic obstructive bronchitis (disorder) |
| 14 | http://snomed.info/sct | 307731004 | Injury of tendon of the rotator cuff of shoulder (disorder) |
| 14 | http://snomed.info/sct | 239872002 | Osteoarthritis of hip (disorder) |
| 14 | http://snomed.info/sct | 43724002 | Chill (finding) |
| 14 | http://snomed.info/sct | 126906006 | Neoplasm of prostate (disorder) |
| 14 | http://snomed.info/sct | 92691004 | Carcinoma in situ of prostate (disorder) |
| 13 | http://snomed.info/sct | 62564004 | Concussion with loss of consciousness (disorder) |
| 13 | http://snomed.info/sct | 109838007 | Overlapping malignant neoplasm of colon (disorder) |
| 13 | http://snomed.info/sct | 427419006 | Transformed migraine (disorder) |
| 13 | http://snomed.info/sct | 233604007 | Pneumonia (disorder) |
| 13 | http://snomed.info/sct | 85116003 | Miscarriage in second trimester (disorder) |
| 12 | http://snomed.info/sct | 315268008 | Suspected prostate cancer (situation) |
| 11 | http://snomed.info/sct | 30832001 | Rupture of patellar tendon (disorder) |
| 11 | http://snomed.info/sct | 162573006 | Suspected lung cancer (situation) |
| 11 | http://snomed.info/sct | 359817006 | Closed fracture of hip (disorder) |
| 10 | http://snomed.info/sct | 876882001 | Died in hospice (finding) |
| 10 | http://snomed.info/sct | 79586000 | Tubal pregnancy (disorder) |
| 10 | http://snomed.info/sct | 76571007 | Septic shock (disorder) |
| 9 | http://snomed.info/sct | 73430006 | Sleep apnea (disorder) |
| 9 | http://snomed.info/sct | 60573004 | Aortic valve stenosis (disorder) |
| 9 | http://snomed.info/sct | 1231000119100 | History of aortic valve replacement (situation) |
| 9 | http://snomed.info/sct | 422587007 | Nausea (finding) |
| 9 | http://snomed.info/sct | 249497008 | Vomiting symptom (finding) |
| 9 | http://snomed.info/sct | 389087006 | Hypoxemia (disorder) |
| 9 | http://snomed.info/sct | 271825005 | Respiratory distress (finding) |
| 9 | http://snomed.info/sct | 127294003 | Traumatic or nontraumatic brain injury (disorder) |
| 9 | http://snomed.info/sct | 68962001 | Muscle pain (finding) |
| 9 | http://snomed.info/sct | 57676002 | Joint pain |
| 9 | http://snomed.info/sct | 49436004 | Atrial fibrillation (disorder) |
| 9 | http://snomed.info/sct | 74400008 | Appendicitis (disorder) |
| 8 | http://snomed.info/sct | 263172003 | Fracture of mandible (disorder) |
| 8 | http://snomed.info/sct | 56786000 | Pulmonic valve stenosis (disorder) |
| 8 | http://snomed.info/sct | 267253006 | Fetus with chromosomal abnormality (disorder) |
| 8 | http://snomed.info/sct | 239720000 | Tear of meniscus of knee (disorder) |
| 8 | http://snomed.info/sct | 25064002 | Headache (finding) |
| 8 | http://snomed.info/sct | 449868002 | Smokes tobacco daily (finding) |
| 8 | http://snomed.info/sct | 230690007 | Cerebrovascular accident (disorder) |
| 7 | http://snomed.info/sct | 5602001 | Opioid abuse |
| 7 | http://snomed.info/sct | 363406005 | Malignant neoplasm of colon (disorder) |
| 7 | http://snomed.info/sct | 230265002 | Familial Alzheimer's disease of early onset (disorder) |
| 7 | http://snomed.info/sct | 67782005 | Acute respiratory distress syndrome (disorder) |
| 7 | http://snomed.info/sct | 408512008 | Body mass index 40+ - severely obese (finding) |
| 7 | http://snomed.info/sct | 254637007 | Non-small cell lung cancer (disorder) |
| 7 | http://snomed.info/sct | 424132000 | Non-small cell carcinoma of lung, TNM stage 1 (disorder) |
| 6 | http://snomed.info/sct | 90560007 | Gout |
| 6 | http://snomed.info/sct | 283545005 | Gunshot wound (disorder) |
| 6 | http://snomed.info/sct | 262574004 | Bullet wound (disorder) |
| 6 | http://snomed.info/sct | 7200002 | Alcoholism (disorder) |
| 6 | http://snomed.info/sct | 83664006 | Idiopathic atrophic hypothyroidism (disorder) |
| 5 | http://snomed.info/sct | 48724000 | Mitral valve regurgitation (disorder) |
| 5 | http://snomed.info/sct | 65710008 | Acute respiratory failure (disorder) |
| 5 | http://snomed.info/sct | 444470001 | Injury of anterior cruciate ligament (disorder) |
| 5 | http://snomed.info/sct | 60234000 | Aortic valve regurgitation (disorder) |
| 5 | http://snomed.info/sct | 81629009 | Traumatic dislocation of temporomandibular joint (disorder) |
| 5 | http://snomed.info/sct | 67787004 | Tongue tie (disorder) |
| 5 | http://snomed.info/sct | 37849005 | Congenital uterine anomaly (disorder) |
| 5 | http://snomed.info/sct | 706870000 | Acute pulmonary embolism (disorder) |
| 4 | http://snomed.info/sct | 132281000119108 | Acute deep venous thrombosis (disorder) |
| 4 | http://snomed.info/sct | 6072007 | Bleeding from anus (disorder) |
| 4 | http://snomed.info/sct | 236077008 | Protracted diarrhea (finding) |
| 4 | http://snomed.info/sct | 109989006 | Multiple myeloma (disorder) |
| 4 | http://snomed.info/sct | 770349000 | Sepsis caused by virus (disorder) |
| 4 | http://snomed.info/sct | 254632001 | Small cell carcinoma of lung (disorder) |
| 4 | http://snomed.info/sct | 67811000119102 | Primary small cell malignant neoplasm of lung, TNM stage 1 (disorder) |
| 4 | http://snomed.info/sct | 93761005 | Primary malignant neoplasm of colon (disorder) |
| 4 | http://snomed.info/sct | 65275009 | Acute cholecystitis (disorder) |
| 4 | http://snomed.info/sct | 235919008 | Gallbladder calculus (disorder) |
| 4 | http://snomed.info/sct | 97331000119101 | Macular edema and retinopathy due to type 2 diabetes mellitus (disorder) |
| 4 | http://snomed.info/sct | 27942005 | Shock (disorder) |
| 3 | http://snomed.info/sct | 312157006 | Infectious mediastinitis (disorder) |
| 3 | http://snomed.info/sct | 698303004 | Awaiting transplantation of bone marrow (situation) |
| 3 | http://snomed.info/sct | 444448004 | Injury of medial collateral ligament of knee (disorder) |
| 3 | http://snomed.info/sct | 267060006 | Diarrhea symptom (finding) |
| 3 | http://snomed.info/sct | 213150003 | Kidney transplant failure and rejection (disorder) |
| 3 | http://snomed.info/sct | 370143000 | Major depressive disorder (disorder) |
| 2 | http://snomed.info/sct | 45816000 | Pyelonephritis (disorder) |
| 2 | http://snomed.info/sct | 94260004 | Metastatic malignant neoplasm to colon (disorder) |
| 2 | http://snomed.info/sct | 153351000119102 | History of peripheral stem cell transplant (situation) |
| 2 | http://snomed.info/sct | 40275004 | Contact dermatitis (disorder) |
| 2 | http://snomed.info/sct | 68235000 | Nasal congestion (finding) |
| 2 | http://snomed.info/sct | 4557003 | Preinfarction syndrome (disorder) |
| 2 | http://snomed.info/sct | 69896004 | Rheumatoid arthritis (disorder) |
| 2 | http://snomed.info/sct | 47505003 | Posttraumatic stress disorder (disorder) |
| 2 | http://snomed.info/sct | 161679004 | History of artificial joint (situation) |
| 2 | http://snomed.info/sct | 108631000119101 | History of autologous bone marrow transplant (situation) |
| 2 | http://snomed.info/sct | 262521009 | Traumatic injury of spinal cord and/or vertebral column (disorder) |
| 1 | http://snomed.info/sct | 234466008 | Acquired coagulation disorder (disorder) |
| 1 | http://snomed.info/sct | 84114007 | Heart failure (disorder) |
| 1 | http://snomed.info/sct | 152621000119105 | History of allotransplantation of bone marrow (situation) |
| 1 | http://snomed.info/sct | 128188000 | Cerebral palsy (disorder) |
| 1 | http://snomed.info/sct | 221360009 | Spasticity (finding) |
| 1 | http://snomed.info/sct | 110359009 | Intellectual disability (disorder) |
| 1 | http://snomed.info/sct | 157265008 | Dislocation of hip joint (disorder) |
| 1 | http://snomed.info/sct | 11625007 | Torus mandibularis (disorder) |
| 1 | http://snomed.info/sct | 94503003 | Metastatic malignant neoplasm to prostate (disorder) |
| 1 | http://snomed.info/sct | 1501000119109 | Proliferative diabetic retinopathy due to type II diabetes mellitus |
| 1 | http://snomed.info/sct | 62479008 | Acquired immune deficiency syndrome (disorder) |
| 1 | http://snomed.info/sct | 86406008 | Human immunodeficiency virus infection (disorder) |
| 1 | http://snomed.info/sct | 1734006 | Fracture of vertebral column with spinal cord injury (disorder) |
| 1 | http://snomed.info/sct | 47693006 | Rupture of appendix (disorder) |
| 1 | http://snomed.info/sct | 204949001 | Renal dysplasia (disorder) |
| 1 | http://snomed.info/sct | 93143009 | Leukemia, disease (disorder) |
| 1 | http://snomed.info/sct | 111287006 | Tricuspid valve regurgitation (disorder) |
| 1 | http://snomed.info/sct | 95417003 | Primary fibromyalgia syndrome (disorder) |
| 1 | http://snomed.info/sct | 200936003 | Lupus erythematosus (disorder) |
| 1 | http://snomed.info/sct | 403192003 | Full thickness burn (disorder) |
| 1 | http://snomed.info/sct | 15724005 | Fracture of vertebral column without spinal cord injury (disorder) |

### CarePlan (37 distinct codes)

| Count | System | Code | Display |
|---|---|---|---|
| 4006 | http://hl7.org/fhir/us/core/CodeSystem/careplan-category | assess-plan | (no display) |
| 603 | http://snomed.info/sct | 53950000 | Respiratory therapy (procedure) |
| 511 | http://snomed.info/sct | 735985000 | Diabetes self management plan (record artifact) |
| 306 | http://snomed.info/sct | 134435003 | Routine antenatal care (regime/therapy) |
| 260 | http://snomed.info/sct | 443402002 | Lifestyle education regarding hypertension (procedure) |
| 209 | http://snomed.info/sct | 384758001 | Self-care interventions (procedure) |
| 208 | http://snomed.info/sct | 773513001 | Physiotherapy care plan (record artifact) |
| 189 | http://snomed.info/sct | 736376001 | Infectious disease care plan (record artifact) |
| 187 | http://snomed.info/sct | 385691007 | Fracture care (regime/therapy) |
| 182 | http://snomed.info/sct | 408869004 | Musculoskeletal care (regime/therapy) |
| 171 | http://snomed.info/sct | 734163000 | Care plan (record artifact) |
| 166 | http://snomed.info/sct | 225358003 | Wound care (regime/therapy) |
| 127 | http://snomed.info/sct | 736285004 | Hyperlipidemia clinical management plan (record artifact) |
| 120 | http://snomed.info/sct | 276239002 | Therapy (regime/therapy) |
| 78 | http://snomed.info/sct | 47387005 | Head injury rehabilitation (regime/therapy) |
| 68 | http://snomed.info/sct | 736353004 | Inpatient care plan (record artifact) |
| 68 | http://snomed.info/sct | 699728000 | Asthma self management (regime/therapy) |
| 60 | http://snomed.info/sct | 133901003 | Burn care (regime/therapy) |
| 55 | http://snomed.info/sct | 736690008 | Dialysis care plan (record artifact) |
| 50 | http://snomed.info/sct | 736372004 | Discharge care plan (record artifact) |
| 48 | http://snomed.info/sct | 170836005 | Allergic disorder monitoring (regime/therapy) |
| 47 | http://snomed.info/sct | 718361005 | Weight management program (regime/therapy) |
| 44 | http://snomed.info/sct | 736283006 | Chronic obstructive pulmonary disease clinical management plan (record artifact) |
| 40 | http://snomed.info/sct | 736252007 | Cancer care plan (record artifact) |
| 36 | http://snomed.info/sct | 386257007 | Dementia management (regime/therapy) |
| 35 | http://snomed.info/sct | 711282006 | Skin condition care (regime/therapy) |
| 34 | http://snomed.info/sct | 735984001 | Heart failure self management plan (record artifact) |
| 28 | http://snomed.info/sct | 737471002 | Minor surgery care management (procedure) |
| 22 | http://snomed.info/sct | 737567002 | Major surgery care management (procedure) |
| 17 | http://snomed.info/sct | 386522008 | Overactivity/inattention behavior management (regime/therapy) |
| 11 | http://snomed.info/sct | 182964004 | Terminal care (regime/therapy) |
| 9 | http://snomed.info/sct | 736254008 | Psychiatry care plan (record artifact) |
| 5 | http://snomed.info/sct | 735321000 | Surgical inpatient care plan (record artifact) |
| 5 | http://snomed.info/sct | 208748005 | Open dislocation of jaw (disorder) |
| 5 | http://snomed.info/sct | 718347000 | Mental health care plan (record artifact) |
| 1 | http://snomed.info/sct | 781087000 | Medical care (regime/therapy) |
| 1 | http://snomed.info/sct | 75162002 | Spinal cord injury rehabilitation (regime/therapy) |

### Procedure (355 distinct codes)

| Count | System | Code | Display |
|---|---|---|---|
| 21277 | http://snomed.info/sct | 171207006 | Depression screening (procedure) |
| 12857 | http://snomed.info/sct | 710824005 | Assessment of health and social care needs (procedure) |
| 12477 | http://snomed.info/sct | 265764009 | Renal dialysis (procedure) |
| 8872 | http://snomed.info/sct | 430193006 | Medication reconciliation (procedure) |
| 8293 | http://snomed.info/sct | 428211000124100 | Assessment of substance use (procedure) |
| 7304 | http://snomed.info/sct | 103697008 | Patient referral for dental care (procedure) |
| 6992 | http://snomed.info/sct | 34043003 | Dental consultation and report (procedure) |
| 6807 | http://snomed.info/sct | 243085009 | Oral health education (procedure) |
| 6760 | http://snomed.info/sct | 225362009 | Dental care (regime/therapy) |
| 6760 | http://snomed.info/sct | 1260009003 | Removal of supragingival plaque and calculus from all teeth using dental instrument (procedure) |
| 6760 | http://snomed.info/sct | 1260010008 | Removal of subgingival plaque and calculus from all teeth using dental instrument (procedure) |
| 6760 | http://snomed.info/sct | 274788003 | Examination of gingivae (procedure) |
| 6696 | http://snomed.info/sct | 710841007 | Assessment of anxiety (procedure) |
| 3901 | http://snomed.info/sct | 713106006 | Screening for drug abuse (procedure) |
| 3896 | http://snomed.info/sct | 410401003 | Nursing care/supplementary surveillance (regime/therapy) |
| 3791 | http://snomed.info/sct | 866148006 | Screening for domestic abuse (procedure) |
| 3781 | http://snomed.info/sct | 763302001 | Assessment using Alcohol Use Disorders Identification Test - Consumption (procedure) |
| 3672 | http://snomed.info/sct | 385763009 | Hospice care (regime/therapy) |
| 3530 | http://snomed.info/sct | 241046008 | Dental plain X-ray bitewing (procedure) |
| 3405 | http://snomed.info/sct | 68071007 | Dental fluoride treatment (procedure) |
| 3172 | http://snomed.info/sct | 762993000 | Assessment using Morse Fall Scale (procedure) |
| 2891 | http://snomed.info/sct | 703423002 | Combined chemotherapy and radiation therapy (procedure) |
| 2518 | http://snomed.info/sct | 398171003 | Hearing examination (procedure) |
| 2485 | http://snomed.info/sct | 274804006 | Evaluation of uterine fundal height (procedure) |
| 2485 | http://snomed.info/sct | 225158009 | Auscultation of the fetal heart (procedure) |
| 2016 | http://snomed.info/sct | 52052004 | Rehabilitation therapy (regime/therapy) |
| 1840 | http://snomed.info/sct | 180256009 | Subcutaneous immunotherapy (procedure) |
| 1319 | http://snomed.info/sct | 81733005 | Dental surgical procedure (procedure) |
| 1319 | http://snomed.info/sct | 456191000124101 | Postoperative care for dental procedure (regime/therapy) |
| 1278 | http://snomed.info/sct | 715252007 | Depression screening using Patient Health Questionnaire Nine Item score (procedure) |
| 1272 | http://snomed.info/sct | 3802001 | Dental application of desensitizing medicament (procedure) |
| 1226 | http://snomed.info/sct | 76601001 | Intramuscular injection (procedure) |
| 1042 | http://snomed.info/sct | 16830007 | Visual acuity testing (procedure) |
| 1042 | http://snomed.info/sct | 252832004 | Intraocular pressure test (procedure) |
| 1042 | http://snomed.info/sct | 55468007 | Ocular slit lamp examination (procedure) |
| 1042 | http://snomed.info/sct | 389153003 | Indirect gonioscopy (procedure) |
| 1042 | http://snomed.info/sct | 314971001 | Camera fundoscopy (procedure) |
| 1042 | http://snomed.info/sct | 722161008 | Diabetic retinal eye exam (procedure) |
| 1021 | http://snomed.info/sct | 64544008 | Gingivectomy or gingivoplasty, per tooth (procedure) |
| 928 | http://snomed.info/sct | 409023009 | Professional / ancillary services care (regime/therapy) |
| 848 | http://snomed.info/sct | 103750000 | Sleep apnea assessment (procedure) |
| 727 | http://snomed.info/sct | 5880005 | Physical examination procedure (procedure) |
| 720 | http://snomed.info/sct | 1259293006 | Application of composite dental filling material to dentin of tooth following fracture of tooth (procedure) |
| 689 | http://snomed.info/sct | 1256042007 | Restoration of tooth with coverage of all cusps using dental filling material (procedure) |
| 677 | http://snomed.info/sct | 73761001 | Colonoscopy (procedure) |
| 630 | http://snomed.info/sct | 127783003 | Spirometry (procedure) |
| 613 | http://snomed.info/sct | 371908008 | Oxygen administration by mask (procedure) |
| 611 | http://snomed.info/sct | 868187001 | Assessment using Car, Relax, Alone, Forget, Friends, Trouble Screening Test (procedure) |
| 586 | http://snomed.info/sct | 431182000 | Placing subject in prone position (procedure) |
| 564 | http://snomed.info/sct | 104091002 | Hemogram, automated, with red blood cells, white blood cells, hemoglobin, hematocrit, indices, platelet count, and manual white blood cell differential (procedure) |
| 538 | http://snomed.info/sct | 700070005 | Optical coherence tomography of retina (procedure) |
| 516 | http://snomed.info/sct | 16335031000119103 | High resolution computed tomography of chest without contrast (procedure) |
| 506 | http://snomed.info/sct | 91251008 | Physical therapy procedure (regime/therapy) |
| 471 | http://snomed.info/sct | 386516004 | Anticipatory guidance (procedure) |
| 469 | http://snomed.info/sct | 252160004 | Standard pregnancy test (procedure) |
| 442 | http://snomed.info/sct | 169230002 | Ultrasound scan for fetal viability (procedure) |
| 398 | http://snomed.info/sct | 90226004 | Cytopathology procedure, preparation of smear, genital source (procedure) |
| 398 | http://snomed.info/sct | 315639002 | Initial patient assessment (procedure) |
| 398 | http://snomed.info/sct | 370789001 | Development of individualized plan of care (procedure) |
| 394 | http://snomed.info/sct | 84478008 | Occupational therapy (regime/therapy) |
| 372 | http://snomed.info/sct | 399208008 | Plain X-ray of chest (procedure) |
| 348 | http://snomed.info/sct | 44608003 | Blood group typing (procedure) |
| 337 | http://snomed.info/sct | 29303009 | Electrocardiographic procedure (procedure) |
| 317 | http://snomed.info/sct | 15081005 | Pulmonary rehabilitation (regime/therapy) |
| 312 | http://snomed.info/sct | 711446003 | Transplantation of kidney regime (regime/therapy) |
| 298 | http://snomed.info/sct | 23426006 | Measurement of respiratory function (procedure) |
| 289 | http://snomed.info/sct | 47758006 | Hepatitis B surface antigen measurement (procedure) |
| 289 | http://snomed.info/sct | 31676001 | Human immunodeficiency virus antigen test (procedure) |
| 289 | http://snomed.info/sct | 310861008 | Chlamydia antigen test (procedure) |
| 289 | http://snomed.info/sct | 165829005 | Gonorrhea infection titer test (procedure) |
| 289 | http://snomed.info/sct | 269828009 | Syphilis infectious titer test (procedure) |
| 289 | http://snomed.info/sct | 117010004 | Urine culture (procedure) |
| 289 | http://snomed.info/sct | 395123002 | Urine screening test for diabetes (procedure) |
| 289 | http://snomed.info/sct | 104375008 | Hepatitis C antibody, confirmatory test (procedure) |
| 289 | http://snomed.info/sct | 314098000 | Rubella screening test (procedure) |
| 289 | http://snomed.info/sct | 104326007 | Measurement of Varicella-zoster virus antibody (procedure) |
| 289 | http://snomed.info/sct | 28163009 | Skin test for tuberculosis, Tine test (procedure) |
| 289 | http://snomed.info/sct | 60218003 | Urinalysis, protein, qualitative (procedure) |
| 289 | http://snomed.info/sct | 443529005 | Detection of chromosomal aneuploidy in prenatal amniotic fluid specimen using fluorescence in situ hybridization screening technique (procedure) |
| 278 | http://snomed.info/sct | 117015009 | Throat culture (procedure) |
| 275 | http://snomed.info/sct | 399014008 | Administration of vaccine product containing only Bordetella pertussis and Clostridium tetani and Corynebacterium diphtheriae antigens (procedure) |
| 275 | http://snomed.info/sct | 268556000 | Urine screening for glucose (procedure) |
| 274 | http://snomed.info/sct | 271442007 | Fetal anatomy study (procedure) |
| 274 | http://snomed.info/sct | 275833003 | Alpha-fetoprotein test - antenatal (procedure) |
| 251 | http://snomed.info/sct | 118001005 | Streptococcus pneumoniae group B antigen assay (procedure) |
| 248 | http://snomed.info/sct | 308283009 | Discharge from hospital (procedure) |
| 230 | http://snomed.info/sct | 229064008 | Movement therapy (regime/therapy) |
| 216 | http://snomed.info/sct | 311555007 | Speech and language therapy regime (regime/therapy) |
| 215 | http://snomed.info/sct | 173291009 | Simple extraction of tooth (procedure) |
| 210 | http://snomed.info/sct | 386216000 | Human parturition, function (observable entity) |
| 208 | http://snomed.info/sct | 40701008 | Echocardiography (procedure) |
| 198 | http://snomed.info/sct | 25656009 | Physical examination, complete (procedure) |
| 196 | http://snomed.info/sct | 441550005 | Urinalysis with reflex to microscopy and culture (procedure) |
| 193 | http://snomed.info/sct | 63332003 | History AND physical examination (procedure) |
| 187 | http://snomed.info/sct | 84100007 | History taking (procedure) |
| 186 | http://snomed.info/sct | 225386006 | Pre-discharge assessment (procedure) |
| 184 | http://snomed.info/sct | 310417005 | Certification procedure (procedure) |
| 184 | http://snomed.info/sct | 185087000 | Notifications (procedure) |
| 175 | http://snomed.info/sct | 234745004 | Take oral or dental impression (procedure) |
| 174 | http://snomed.info/sct | 1269321004 | Fitting of denture (procedure) |
| 172 | http://snomed.info/sct | 183519002 | Referral to cardiology service (procedure) |
| 164 | http://snomed.info/sct | 58000006 | Patient discharge (procedure) |
| 163 | http://snomed.info/sct | 288086009 | Suture open wound (procedure) |
| 160 | http://snomed.info/sct | 133899007 | Postoperative care (regime/therapy) |
| 157 | http://snomed.info/sct | 65200003 | Insertion of intrauterine contraceptive device (procedure) |
| 155 | http://snomed.info/sct | 169553002 | Implantation of subcutaneous contraceptive (procedure) |
| 154 | http://snomed.info/sct | 223470000 | Discussion about signs and symptoms (procedure) |
| 154 | http://snomed.info/sct | 281789004 | Antibiotic therapy (procedure) |
| 152 | http://snomed.info/sct | 473231009 | Renal disorder medication review (procedure) |
| 151 | http://snomed.info/sct | 71651007 | Mammography (procedure) |
| 145 | http://snomed.info/sct | 67879005 | History and physical examination, limited (procedure) |
| 143 | http://snomed.info/sct | 57617002 | Urine specimen collection (procedure) |
| 140 | http://snomed.info/sct | 370995009 | Health risks education (procedure) |
| 140 | http://snomed.info/sct | 33367005 | Angiography of coronary artery (procedure) |
| 138 | http://snomed.info/sct | 274474001 | Bone immobilization (procedure) |
| 137 | http://snomed.info/sct | 228557008 | Cognitive and behavioral therapy (regime/therapy) |
| 126 | http://snomed.info/sct | 698314001 | Consultation for treatment (procedure) |
| 126 | http://snomed.info/sct | 1004045004 | Intravitreal injection of anti-vascular endothelial growth factor (procedure) |
| 125 | http://snomed.info/sct | 312681000 | Bone density scan (procedure) |
| 121 | http://snomed.info/sct | 274031008 | Rectal polypectomy (procedure) |
| 121 | http://snomed.info/sct | 14768001 | Peripheral blood smear interpretation (procedure) |
| 120 | http://snomed.info/sct | 415300000 | Review of systems (procedure) |
| 120 | http://snomed.info/sct | 162676008 | Brief general examination (procedure) |
| 113 | http://snomed.info/sct | 736169004 | Post anesthesia care management (procedure) |
| 109 | http://snomed.info/sct | 51116004 | Passive immunization (procedure) |
| 109 | http://snomed.info/sct | 71493000 | Transfusion of packed red blood cells (procedure) |
| 109 | http://snomed.info/sct | 35025007 | Manual pelvic examination (procedure) |
| 104 | http://snomed.info/sct | 269911007 | Sputum examination (procedure) |
| 102 | http://snomed.info/sct | 33195004 | External beam radiation therapy procedure (procedure) |
| 101 | http://snomed.info/sct | 261352009 | Face mask (physical object) |
| 101 | http://snomed.info/sct | 386053000 | Evaluation procedure (procedure) |
| 100 | http://snomed.info/sct | 104435004 | Screening for occult blood in feces (procedure) |
| 98 | http://snomed.info/sct | 1263416007 | Removal of intrauterine contraceptive device (procedure) |
| 93 | http://snomed.info/sct | 301807007 | Removal of subcutaneous contraceptive (procedure) |
| 89 | http://snomed.info/sct | 395142003 | Allergy screening test (procedure) |
| 84 | http://snomed.info/sct | 65546002 | Extraction of wisdom tooth (procedure) |
| 84 | http://snomed.info/sct | 1287742003 | Radiotherapy (procedure) |
| 82 | http://snomed.info/sct | 10383002 | Counseling for termination of pregnancy (procedure) |
| 82 | http://snomed.info/sct | 714812005 | Induced termination of pregnancy (procedure) |
| 82 | http://snomed.info/sct | 386394001 | Pregnancy termination care (regime/therapy) |
| 80 | http://snomed.info/sct | 473220001 | Hematologic disorder medication review (procedure) |
| 79 | http://snomed.info/sct | 415070008 | Percutaneous coronary intervention |
| 79 | http://snomed.info/sct | 85548006 | Episiotomy (procedure) |
| 71 | http://snomed.info/sct | 410006001 | Digital examination of rectum (procedure) |
| 68 | http://snomed.info/sct | 290045001 | Kitchen practice (regime/therapy) |
| 68 | http://snomed.info/sct | 229095001 | Exercise class (regime/therapy) |
| 68 | http://snomed.info/sct | 385798007 | Radiation therapy care (regime/therapy) |
| 67 | http://snomed.info/sct | 46706006 | Replacement of contraceptive intrauterine device (procedure) |
| 61 | http://snomed.info/sct | 410770002 | Administration of anesthesia for procedure (procedure) |
| 61 | http://snomed.info/sct | 52765003 | Intubation (procedure) |
| 59 | http://snomed.info/sct | 110467000 | Pre-surgery testing (procedure) |
| 59 | http://snomed.info/sct | 709138001 | Notification of treatment plan (procedure) |
| 59 | http://snomed.info/sct | 410538000 | Scheduling (procedure) |
| 58 | http://snomed.info/sct | 306185001 | Referral to cardiac surgery service (procedure) |
| 57 | http://snomed.info/sct | 392247006 | Insertion of catheter into artery (procedure) |
| 57 | http://snomed.info/sct | 243063003 | Postoperative procedure education (procedure) |
| 57 | http://snomed.info/sct | 302761001 | Walking exercise test (procedure) |
| 57 | http://snomed.info/sct | 252482003 | Stair-climbing test (procedure) |
| 56 | http://snomed.info/sct | 306706006 | Discharge to ward (procedure) |
| 56 | http://snomed.info/sct | 433236007 | Transthoracic echocardiography (procedure) |
| 56 | http://snomed.info/sct | 311791003 | Information gathering (procedure) |
| 54 | http://snomed.info/sct | 65677008 | Pulmonary catheterization with Swan-Ganz catheter (procedure) |
| 54 | http://snomed.info/sct | 223495004 | Preparation of patient for procedure (regime/therapy) |
| 54 | http://snomed.info/sct | 359672006 | Median sternotomy (procedure) |
| 54 | http://snomed.info/sct | 23745001 | Documentation procedure (procedure) |
| 54 | http://snomed.info/sct | 271280005 | Removal of endotracheal tube (procedure) |
| 53 | http://snomed.info/sct | 386478007 | Triage: emergency center (procedure) |
| 53 | http://snomed.info/sct | 61746007 | Taking patient vital signs (procedure) |
| 53 | http://snomed.info/sct | 14736009 | History and physical examination with evaluation and management of patient (procedure) |
| 52 | http://snomed.info/sct | 423475008 | Heart failure education (procedure) |
| 51 | http://snomed.info/sct | 18946005 | Epidural anesthesia (procedure) |
| 50 | http://snomed.info/sct | 440546007 | Discussion about pregnancy (procedure) |
| 48 | http://snomed.info/sct | 31208007 | Medical induction of labor (procedure) |
| 47 | http://snomed.info/sct | 284053004 | Tooth socket procedure (procedure) |
| 45 | http://snomed.info/sct | 169673001 | Antenatal RhD antibody screening (procedure) |
| 45 | http://snomed.info/sct | 305428000 | Admission to orthopedic department (procedure) |
| 45 | http://snomed.info/sct | 367336001 | Chemotherapy (procedure) |
| 43 | http://snomed.info/sct | 713026007 | Plain X-ray of humerus (procedure) |
| 42 | http://snomed.info/sct | 11466000 | Cesarean section (procedure) |
| 40 | http://snomed.info/sct | 313660005 | Absolute CD4 count procedure (procedure) |
| 38 | http://snomed.info/sct | 762998009 | Assessment using New York Heart Association Classification (procedure) |
| 38 | http://snomed.info/sct | 9564003 | Complete blood count with white cell differential, automated (procedure) |
| 36 | http://snomed.info/sct | 306316000 | Referral to transplant surgeon (procedure) |
| 35 | http://snomed.info/sct | 711069006 | Coordination of care plan (procedure) |
| 35 | http://snomed.info/sct | 1290459008 | Plain X-ray of ankle region (procedure) |
| 34 | http://snomed.info/sct | 168594001 | Plain X-ray of clavicle (procedure) |
| 34 | http://snomed.info/sct | 384700001 | Injection of tetanus antitoxin (procedure) |
| 33 | http://snomed.info/sct | 54550000 | Electroencephalogram (procedure) |
| 32 | http://snomed.info/sct | 42825003 | Cannulation (procedure) |
| 32 | http://snomed.info/sct | 63697000 | Cardiopulmonary bypass operation (procedure) |
| 32 | http://snomed.info/sct | 301882004 | Placement of aortic cross clamp (procedure) |
| 32 | http://snomed.info/sct | 8290005 | Induced cardioplegia (procedure) |
| 32 | http://snomed.info/sct | 301884003 | Removal of aortic cross clamp (procedure) |
| 32 | http://snomed.info/sct | 233553003 | Vascular cannula removal (procedure) |
| 32 | http://snomed.info/sct | 713024005 | Plain X-ray of wrist region (procedure) |
| 32 | http://snomed.info/sct | 315124004 | Human immunodeficiency virus viral load (procedure) |
| 31 | http://snomed.info/sct | 428830000 | Pretransplant evaluation of kidney recipient (procedure) |
| 31 | http://snomed.info/sct | 70536003 | Transplant of kidney (procedure) |
| 31 | http://snomed.info/sct | 698560000 | Referral to sleep apnea clinic (procedure) |
| 30 | http://snomed.info/sct | 15220000 | Laboratory test (procedure) |
| 30 | http://snomed.info/sct | 430701006 | Resuscitation using intravenous fluid (procedure) |
| 29 | http://snomed.info/sct | 232717009 | Coronary artery bypass grafting (procedure) |
| 28 | http://snomed.info/sct | 710839006 | Assessment of cardiac status using monitoring device (procedure) |
| 28 | http://snomed.info/sct | 165197003 | Diagnostic assessment (procedure) |
| 28 | http://snomed.info/sct | 390791001 | Referral for echocardiography (procedure) |
| 28 | http://snomed.info/sct | 237001001 | Augmentation of labor (procedure) |
| 28 | http://snomed.info/sct | 417511005 | Referral to home health care service (procedure) |
| 28 | http://snomed.info/sct | 200619008 | Comprehensive interview and evaluation (procedure) |
| 27 | http://snomed.info/sct | 1290407002 | Plain X-ray of knee region (procedure) |
| 27 | http://snomed.info/sct | 392091000 | Care regimes assessment (procedure) |
| 26 | http://snomed.info/sct | 385781007 | Home health aide service (regime/therapy) |
| 25 | http://snomed.info/sct | 313191000 | Injection of epinephrine (procedure) |
| 23 | http://snomed.info/sct | 306206005 | Referral to service (procedure) |
| 23 | http://snomed.info/sct | 268533009 | Sterilization education (procedure) |
| 23 | http://snomed.info/sct | 287664005 | Ligation of bilateral fallopian tubes (procedure) |
| 23 | http://snomed.info/sct | 183444007 | Referral for further care (procedure) |
| 21 | http://snomed.info/sct | 449214001 | Transfer to stepdown unit (procedure) |
| 20 | http://snomed.info/sct | 43075005 | Partial resection of colon (procedure) |
| 20 | http://snomed.info/sct | 234687006 | Grafting of periodontal bone defect (procedure) |
| 20 | http://snomed.info/sct | 448337001 | Telemedicine consultation with patient (procedure) |
| 20 | http://snomed.info/sct | 225338004 | Risk assessment (procedure) |
| 20 | http://snomed.info/sct | 418824004 | Off-pump coronary artery bypass (procedure) |
| 19 | http://snomed.info/sct | 305351004 | Admission to intensive care unit (procedure) |
| 17 | http://snomed.info/sct | 367494004 | Premature birth of newborn (finding) |
| 17 | http://snomed.info/sct | 79345008 | Excision of maxillary torus palatinus (procedure) |
| 17 | http://snomed.info/sct | 699253003 | Surgical manipulation of joint of knee (procedure) |
| 16 | http://snomed.info/sct | 236974004 | Instrumental delivery (procedure) |
| 16 | http://snomed.info/sct | 397539000 | Grid retinal photocoagulation (procedure) |
| 15 | http://snomed.info/sct | 82808001 | Sleep apnea monitoring with alarm (regime/therapy) |
| 14 | http://snomed.info/sct | 171231001 | Asthma screening (procedure) |
| 13 | http://snomed.info/sct | 122856003 | Oral examination (procedure) |
| 13 | http://snomed.info/sct | 69212005 | Range of motion testing (procedure) |
| 13 | http://snomed.info/sct | 180178009 | Continuous subcutaneous infusion of insulin (procedure) |
| 12 | http://snomed.info/sct | 65575008 | Biopsy of prostate (procedure) |
| 11 | http://snomed.info/sct | 418891003 | Computed tomography of chest and abdomen (procedure) |
| 11 | http://snomed.info/sct | 698354004 | Magnetic resonance imaging for measurement of brain volume (procedure) |
| 11 | http://snomed.info/sct | 243150007 | Assist control ventilation (regime/therapy) |
| 11 | http://snomed.info/sct | 713021002 | Plain X-ray of pelvis (procedure) |
| 10 | http://snomed.info/sct | 1290789000 | Plain X-ray of mandible (procedure) |
| 10 | http://snomed.info/sct | 76164006 | Biopsy of colon (procedure) |
| 10 | http://snomed.info/sct | 26604007 | Complete blood count (procedure) |
| 9 | http://snomed.info/sct | 80146002 | Excision of appendix (procedure) |
| 8 | http://snomed.info/sct | 90470006 | Prostatectomy (procedure) |
| 8 | http://snomed.info/sct | 180207008 | Intravenous blood transfusion of packed cells (procedure) |
| 8 | http://snomed.info/sct | 85765000 | Fiberoptic bronchoscopy (procedure) |
| 8 | http://snomed.info/sct | 866146005 | Serum metabolic panel (procedure) |
| 8 | http://snomed.info/sct | 433112001 | Percutaneous mechanical thrombectomy of portal vein using fluoroscopic guidance with contrast (procedure) |
| 7 | http://snomed.info/sct | 24832002 | Closed reduction of mandibular fracture (procedure) |
| 7 | http://snomed.info/sct | 413180006 | Pan retinal photocoagulation for diabetes (procedure) |
| 7 | http://snomed.info/sct | 183856001 | Referral to hypertension clinic (procedure) |
| 7 | http://snomed.info/sct | 112790001 | Nasal sinus endoscopy (procedure) |
| 6 | http://snomed.info/sct | 76746007 | Cardiovascular stress testing (procedure) |
| 6 | http://snomed.info/sct | 445912000 | Excision of fallopian tube and surgical removal of ectopic pregnancy (procedure) |
| 6 | http://snomed.info/sct | 116861002 | Transfusion of fresh frozen plasma (procedure) |
| 6 | http://snomed.info/sct | 122548005 | Biopsy of breast (procedure) |
| 6 | http://snomed.info/sct | 434363004 | Human epidermal growth factor receptor 2 gene detection by fluorescence in situ hybridization (procedure) |
| 6 | http://snomed.info/sct | 433114000 | Human epidermal growth factor receptor 2 gene detection by immunohistochemistry (procedure) |
| 6 | http://snomed.info/sct | 223487003 | Discussion about options (procedure) |
| 6 | http://snomed.info/sct | 392021009 | Lumpectomy of breast (procedure) |
| 5 | http://snomed.info/sct | 37542007 | Posttreatment stabilization, orthodontic device (procedure) |
| 5 | http://snomed.info/sct | 414088005 | Emergency coronary artery bypass graft (procedure) |
| 5 | http://snomed.info/sct | 365853002 | Imaging finding (finding) |
| 5 | http://snomed.info/sct | 183976008 | Operative procedure planned (situation) |
| 5 | http://snomed.info/sct | 709010006 | Liaising with referral source (procedure) |
| 5 | http://snomed.info/sct | 312853008 | Medical records review (procedure) |
| 5 | http://snomed.info/sct | 418023006 | Computed tomography of chest, abdomen and pelvis (procedure) |
| 5 | http://snomed.info/sct | 772071006 | Referral to dentist (procedure) |
| 5 | http://snomed.info/sct | 252480006 | Simple walk test (procedure) |
| 5 | http://snomed.info/sct | 763228001 | Assessment using Canadian Study of Health and Aging Clinical Frailty Scale (procedure) |
| 5 | http://snomed.info/sct | 445988008 | Assessment using health assessment questionnaire (procedure) |
| 5 | http://snomed.info/sct | 312384001 | Multidisciplinary assessment (procedure) |
| 5 | http://snomed.info/sct | 133900002 | Intraoperative care (regime/therapy) |
| 5 | http://snomed.info/sct | 34896006 | Incision (procedure) |
| 5 | http://snomed.info/sct | 58828004 | Application of dressing, sterile (procedure) |
| 5 | http://snomed.info/sct | 37729005 | Patient transfer, in-hospital (procedure) |
| 5 | http://snomed.info/sct | 40617009 | Artificial ventilation (regime/therapy) |
| 5 | http://snomed.info/sct | 243174005 | Weaning from mechanically assisted ventilation (regime/therapy) |
| 5 | http://snomed.info/sct | 22523008 | Vasectomy (procedure) |
| 5 | http://snomed.info/sct | 88039007 | Transplant of lung (procedure) |
| 5 | http://snomed.info/sct | 225415001 | Close observation (regime/therapy) |
| 5 | http://snomed.info/sct | 241615005 | Magnetic resonance imaging of breast (procedure) |
| 5 | http://snomed.info/sct | 23933004 | Excision of lingual frenum (procedure) |
| 5 | http://snomed.info/sct | 12719002 | Platelet transfusion (procedure) |
| 4 | http://snomed.info/sct | 429609002 | Lung volume reduction surgery (procedure) |
| 4 | http://snomed.info/sct | 268400002 | 12 lead electrocardiogram (procedure) |
| 4 | http://snomed.info/sct | 180325003 | Direct current cardioversion (procedure) |
| 4 | http://snomed.info/sct | 236931002 | Methotrexate injection into tubal pregnancy (procedure) |
| 4 | http://snomed.info/sct | 426701000119108 | Ultrasonography of abdomen, right upper quadrant and epigastrium (procedure) |
| 4 | http://snomed.info/sct | 225337009 | Suicide risk assessment (procedure) |
| 4 | http://snomed.info/sct | 234262008 | Excision of axillary lymph node (procedure) |
| 3 | http://snomed.info/sct | 26212005 | Replacement of aortic valve (procedure) |
| 3 | http://snomed.info/sct | 105376000 | Transesophageal echocardiography (procedure) |
| 3 | http://snomed.info/sct | 304532001 | Treatment failure risk education (procedure) |
| 3 | http://snomed.info/sct | 304531008 | Treatment side effects education (procedure) |
| 3 | http://snomed.info/sct | 394894008 | Pre-operative chemotherapy (procedure) |
| 3 | http://snomed.info/sct | 179632003 | Closed reduction of dislocation of temporomandibular joint (procedure) |
| 3 | http://snomed.info/sct | 241055006 | Mammogram - symptomatic (procedure) |
| 3 | http://snomed.info/sct | 170245002 | Child examination: school screening (procedure) |
| 3 | http://snomed.info/sct | 308481009 | Referral to orthopedic surgeon (procedure) |
| 3 | http://snomed.info/sct | 417656005 | Osteopathic postural examination (procedure) |
| 3 | http://snomed.info/sct | 183830008 | Referral for X-ray (procedure) |
| 3 | http://snomed.info/sct | 1290953004 | Plain X-ray of spine and pelvis (procedure) |
| 3 | http://snomed.info/sct | 122869004 | Measurement procedure (procedure) |
| 3 | http://snomed.info/sct | 45595009 | Laparoscopic cholecystectomy (procedure) |
| 3 | http://snomed.info/sct | 24623002 | Screening mammography (procedure) |
| 2 | http://snomed.info/sct | 410011004 | Administration of anesthesia AND/OR sedation (procedure) |
| 2 | http://snomed.info/sct | 773996000 | Transcatheter aortic valve implantation (procedure) |
| 2 | http://snomed.info/sct | 305342007 | Admission to ward (procedure) |
| 2 | http://snomed.info/sct | 371361000119107 | Comprehensive metabolic panel (procedure) |
| 2 | http://snomed.info/sct | 234336002 | Hemopoietic stem cell transplant (procedure) |
| 2 | http://snomed.info/sct | 78429003 | Referral to physical rehabilitation service (procedure) |
| 2 | http://snomed.info/sct | 305433001 | Admission to trauma surgery department (procedure) |
| 2 | http://snomed.info/sct | 432231006 | Fine needle aspiration biopsy of lung (procedure) |
| 2 | http://snomed.info/sct | 387685009 | Surgical manipulation of shoulder joint (procedure) |
| 2 | http://snomed.info/sct | 373786007 | Reasons for treatment delay (finding) |
| 2 | http://snomed.info/sct | 412809002 | Viral hepatitis screening test (procedure) |
| 2 | http://snomed.info/sct | 171122006 | Hepatitis B screening (procedure) |
| 2 | http://snomed.info/sct | 413107006 | Hepatitis C screening (procedure) |
| 2 | http://snomed.info/sct | 313398001 | Hepatitis antibody test (procedure) |
| 2 | http://snomed.info/sct | 171126009 | Tuberculosis screening (procedure) |
| 2 | http://snomed.info/sct | 171128005 | Venereal disease screening (procedure) |
| 2 | http://snomed.info/sct | 104308009 | Serologic test for Toxoplasma gondii (procedure) |
| 2 | http://snomed.info/sct | 711018006 | Assessment of social support (procedure) |
| 2 | http://snomed.info/sct | 709506004 | Assessment of readiness for disclosure of health status (procedure) |
| 2 | http://snomed.info/sct | 733863009 | Assessment of readiness for self-management (procedure) |
| 2 | http://snomed.info/sct | 410314003 | Health promotion education, guidance, and counseling (procedure) |
| 2 | http://snomed.info/sct | 225297008 | Care planning and problem solving actions (procedure) |
| 2 | http://snomed.info/sct | 385892002 | Mental health screening (procedure) |
| 2 | http://snomed.info/sct | 38102005 | Cholecystectomy (procedure) |
| 2 | http://snomed.info/sct | 122460008 | Reexploration procedure (procedure) |
| 1 | http://snomed.info/sct | 116863004 | Transfusion of red blood cells (procedure) |
| 1 | http://snomed.info/sct | 30088009 | Blood culture (procedure) |
| 1 | http://snomed.info/sct | 9905009 | Loop colostomy (procedure) |
| 1 | http://snomed.info/sct | 446573003 | Continuous positive airway pressure titration (procedure) |
| 1 | http://snomed.info/sct | 112798008 | Insertion of endotracheal tube (procedure) |
| 1 | http://snomed.info/sct | 58390007 | Allogeneic bone marrow transplantation (procedure) |
| 1 | http://snomed.info/sct | 23183008 | Excision of lingual torus (procedure) |
| 1 | http://snomed.info/sct | 167995008 | Sputum microscopy (procedure) |
| 1 | http://snomed.info/sct | 171121004 | Human immunodeficiency virus screening (procedure) |
| 1 | http://snomed.info/sct | 313077009 | Human immunodeficiency virus counseling (procedure) |
| 1 | http://snomed.info/sct | 3457005 | Patient referral (procedure) |
| 1 | http://snomed.info/sct | 167252002 | Urine pregnancy test (procedure) |
| 1 | http://snomed.info/sct | 446987006 | Determination of susceptibility of Human immunodeficiency virus 1 to panel of antiretroviral drugs using genotypic technique (procedure) |
| 1 | http://snomed.info/sct | 609588000 | Prosthetic total arthroplasty of knee joint (procedure) |
| 1 | http://snomed.info/sct | 177157003 | Spontaneous breech delivery (procedure) |
| 1 | http://snomed.info/sct | 18286008 | Catheter ablation of tissue of heart (procedure) |
| 1 | http://snomed.info/sct | 709979004 | Doppler ultrasonography of artery (procedure) |
| 1 | http://snomed.info/sct | 303653007 | Computed tomography of head (procedure) |
| 1 | http://snomed.info/sct | 392023007 | Excision of lesion of breast (procedure) |
| 1 | http://snomed.info/sct | 396487001 | Sentinel lymph node biopsy (procedure) |
| 1 | http://snomed.info/sct | 443497002 | Excision of sentinel lymph node (procedure) |
| 1 | http://snomed.info/sct | 183418007 | Social case work (regime/therapy) |
| 1 | http://snomed.info/sct | 1571000087109 | Ultrasonography of bilateral breasts (procedure) |
| 1 | http://snomed.info/sct | 183450002 | Admission to burn unit (procedure) |
| 1 | http://snomed.info/sct | 305340004 | Admission to long stay hospital (procedure) |

### MedicationRequest (190 distinct codes)

| Count | System | Code | Display |
|---|---|---|---|
| 6320 | http://www.nlm.nih.gov/research/umls/rxnorm | 106892 | insulin isophane, human 70 UNT/ML / insulin, regular, human 30 UNT/ML Injectable Suspension [Humulin] |
| 6235 | http://www.nlm.nih.gov/research/umls/rxnorm | 314076 | lisinopril 10 MG Oral Tablet |
| 4843 | http://www.nlm.nih.gov/research/umls/rxnorm | 310798 | Hydrochlorothiazide 25 MG Oral Tablet |
| 4116 | http://www.nlm.nih.gov/research/umls/rxnorm | 308136 | amLODIPine 2.5 MG Oral Tablet |
| 3423 | http://www.nlm.nih.gov/research/umls/rxnorm | 860975 | 24 HR Metformin hydrochloride 500 MG Extended Release Oral Tablet |
| 1155 | http://www.nlm.nih.gov/research/umls/rxnorm | 314231 | Simvastatin 10 MG Oral Tablet |
| 1109 | http://www.nlm.nih.gov/research/umls/rxnorm | 1664463 | 24 HR tacrolimus 1 MG Extended Release Oral Tablet [Envarsus] |
| 892 | http://www.nlm.nih.gov/research/umls/rxnorm | 904419 | Alendronic acid 10 MG Oral Tablet |
| 838 | http://www.nlm.nih.gov/research/umls/rxnorm | 206905 | Ibuprofen 400 MG Oral Tablet [Ibu] |
| 694 | http://www.nlm.nih.gov/research/umls/rxnorm | 209387 | Acetaminophen 325 MG Oral Tablet [Tylenol] |
| 680 | http://www.nlm.nih.gov/research/umls/rxnorm | 856987 | Acetaminophen 300 MG / Hydrocodone Bitartrate 5 MG Oral Tablet |
| 679 | http://www.nlm.nih.gov/research/umls/rxnorm | 245314 | albuterol 5 MG/ML Inhalation Solution |
| 662 | http://www.nlm.nih.gov/research/umls/rxnorm | 896209 | 60 ACTUAT Fluticasone propionate 0.25 MG/ACTUAT / salmeterol 0.05 MG/ACTUAT Dry Powder Inhaler |
| 612 | http://www.nlm.nih.gov/research/umls/rxnorm | 313782 | Acetaminophen 325 MG Oral Tablet |
| 540 | http://www.nlm.nih.gov/research/umls/rxnorm | 630208 | albuterol 0.83 MG/ML Inhalation Solution |
| 532 | http://www.nlm.nih.gov/research/umls/rxnorm | 1049625 | Acetaminophen 325 MG / Oxycodone Hydrochloride 10 MG Oral Tablet [Percocet] |
| 495 | http://www.nlm.nih.gov/research/umls/rxnorm | 897685 | verapamil hydrochloride 80 MG Oral Tablet [Calan] |
| 495 | http://www.nlm.nih.gov/research/umls/rxnorm | 855332 | Warfarin Sodium 5 MG Oral Tablet |
| 495 | http://www.nlm.nih.gov/research/umls/rxnorm | 197604 | Digoxin 0.125 MG Oral Tablet |
| 411 | http://www.nlm.nih.gov/research/umls/rxnorm | 895996 | 120 ACTUAT fluticasone propionate 0.044 MG/ACTUAT Metered Dose Inhaler [Flovent] |
| 303 | http://www.nlm.nih.gov/research/umls/rxnorm | 835603 | tramadol hydrochloride 50 MG Oral Tablet |
| 278 | http://www.nlm.nih.gov/research/umls/rxnorm | 849574 | Naproxen sodium 220 MG Oral Tablet |
| 272 | http://www.nlm.nih.gov/research/umls/rxnorm | 351109 | budesonide 0.25 MG/ML Inhalation Suspension |
| 269 | http://www.nlm.nih.gov/research/umls/rxnorm | 745752 | NDA021457 200 ACTUAT albuterol 0.09 MG/ACTUAT Metered Dose Inhaler [ProAir] |
| 264 | http://www.nlm.nih.gov/research/umls/rxnorm | 562251 | Amoxicillin 250 MG / Clavulanate 125 MG Oral Tablet |
| 212 | http://www.nlm.nih.gov/research/umls/rxnorm | 245134 | 72 HR Fentanyl 0.025 MG/HR Transdermal System |
| 201 | http://www.nlm.nih.gov/research/umls/rxnorm | 313988 | Furosemide 40 MG Oral Tablet |
| 199 | http://www.nlm.nih.gov/research/umls/rxnorm | 310965 | Ibuprofen 200 MG Oral Tablet |
| 199 | http://www.nlm.nih.gov/research/umls/rxnorm | 705129 | Nitroglycerin 0.4 MG/ACTUAT Mucosal Spray |
| 193 | http://www.nlm.nih.gov/research/umls/rxnorm | 866412 | 24 HR metoprolol succinate 100 MG Extended Release Oral Tablet |
| 189 | http://www.nlm.nih.gov/research/umls/rxnorm | 1860491 | 12 HR Hydrocodone Bitartrate 10 MG Extended Release Oral Capsule |
| 177 | http://www.nlm.nih.gov/research/umls/rxnorm | 309362 | Clopidogrel 75 MG Oral Tablet |
| 174 | http://www.nlm.nih.gov/research/umls/rxnorm | 312961 | Simvastatin 20 MG Oral Tablet |
| 174 | http://www.nlm.nih.gov/research/umls/rxnorm | 1049504 | Abuse-Deterrent 12 HR Oxycodone Hydrochloride 10 MG Extended Release Oral Tablet [Oxycontin] |
| 158 | http://www.nlm.nih.gov/research/umls/rxnorm | 896001 | 120 ACTUAT fluticasone propionate 0.11 MG/ACTUAT Metered Dose Inhaler [Flovent] |
| 155 | http://www.nlm.nih.gov/research/umls/rxnorm | 1043400 | Acetaminophen 21.7 MG/ML / Dextromethorphan Hydrobromide 1 MG/ML / doxylamine succinate 0.417 MG/ML Oral Solution |
| 138 | http://www.nlm.nih.gov/research/umls/rxnorm | 349094 | budesonide 0.125 MG/ML Inhalation Suspension |
| 134 | http://www.nlm.nih.gov/research/umls/rxnorm | 200033 | carvedilol 25 MG Oral Tablet |
| 128 | http://www.nlm.nih.gov/research/umls/rxnorm | 993770 | Acetaminophen 300 MG / Codeine Phosphate 15 MG Oral Tablet |
| 127 | http://www.nlm.nih.gov/research/umls/rxnorm | 1870230 | NDA020800 0.3 ML Epinephrine 1 MG/ML Auto-Injector |
| 124 | http://www.nlm.nih.gov/research/umls/rxnorm | 757594 | {28 (norethindrone 0.35 MG Oral Tablet) } Pack [Jolivette 28 Day] |
| 114 | http://www.nlm.nih.gov/research/umls/rxnorm | 314077 | lisinopril 20 MG Oral Tablet |
| 113 | http://www.nlm.nih.gov/research/umls/rxnorm | 198405 | Ibuprofen 100 MG Oral Tablet |
| 111 | http://www.nlm.nih.gov/research/umls/rxnorm | 859088 | NDA020983 200 ACTUAT albuterol 0.09 MG/ACTUAT Metered Dose Inhaler [Ventolin] |
| 110 | http://www.nlm.nih.gov/research/umls/rxnorm | 748962 | {28 (norethindrone 0.35 MG Oral Tablet) } Pack [Camila 28 Day] |
| 110 | http://www.nlm.nih.gov/research/umls/rxnorm | 979492 | losartan potassium 50 MG Oral Tablet |
| 109 | http://www.nlm.nih.gov/research/umls/rxnorm | 313820 | Acetaminophen 160 MG Chewable Tablet |
| 104 | http://www.nlm.nih.gov/research/umls/rxnorm | 351137 | albuterol 0.21 MG/ML Inhalation Solution |
| 91 | http://www.nlm.nih.gov/research/umls/rxnorm | 616830 | budesonide 0.125 MG/ML Inhalation Suspension [Pulmicort] |
| 87 | http://www.nlm.nih.gov/research/umls/rxnorm | 831533 | {28 (norethindrone 0.35 MG Oral Tablet) } Pack [Errin 28 Day] |
| 86 | http://www.nlm.nih.gov/research/umls/rxnorm | 351266 | buprenorphine 2 MG / naloxone 0.5 MG Sublingual Tablet |
| 84 | http://www.nlm.nih.gov/research/umls/rxnorm | 856987 | Acetaminophen 300 MG / HYDROcodone Bitartrate 5 MG Oral Tablet |
| 83 | http://www.nlm.nih.gov/research/umls/rxnorm | 834102 | Penicillin V Potassium 500 MG Oral Tablet |
| 81 | http://www.nlm.nih.gov/research/umls/rxnorm | 308192 | Amoxicillin 500 MG Oral Tablet |
| 78 | http://www.nlm.nih.gov/research/umls/rxnorm | 751905 | {7 (ethinyl estradiol 0.035 MG / norgestimate 0.18 MG Oral Tablet) / 7 (ethinyl estradiol 0.035 MG / norgestimate 0.215 MG Oral Tablet) / 7 (ethinyl estradiol 0.035 MG / norgestimate 0.25 MG Oral Tablet) / 7 (inert ingredients 1 MG Oral Tablet) } Pack [Trinessa 28 Day] |
| 77 | http://www.nlm.nih.gov/research/umls/rxnorm | 834061 | Penicillin V Potassium 250 MG Oral Tablet |
| 71 | http://www.nlm.nih.gov/research/umls/rxnorm | 748856 | {24 (drospirenone 3 MG / ethinyl estradiol 0.02 MG Oral Tablet) / 4 (inert ingredients 1 MG Oral Tablet) } Pack [Yaz 28 Day] |
| 68 | http://www.nlm.nih.gov/research/umls/rxnorm | 310325 | ferrous sulfate 325 MG Oral Tablet |
| 67 | http://www.nlm.nih.gov/research/umls/rxnorm | 748879 | {21 (ethinyl estradiol 0.03 MG / levonorgestrel 0.15 MG Oral Tablet) / 7 (inert ingredients 1 MG Oral Tablet) } Pack [Levora 0.15/30 28 Day] |
| 64 | http://www.nlm.nih.gov/research/umls/rxnorm | 1860154 | Abuse-Deterrent 12 HR Oxycodone Hydrochloride 15 MG Extended Release Oral Tablet |
| 63 | http://www.nlm.nih.gov/research/umls/rxnorm | 1049221 | Acetaminophen 325 MG / Oxycodone Hydrochloride 5 MG Oral Tablet |
| 60 | http://www.nlm.nih.gov/research/umls/rxnorm | 978950 | {5 (dienogest 2 MG / estradiol valerate 2 MG Oral Tablet) / 17 (dienogest 3 MG / estradiol valerate 2 MG Oral Tablet) / 2 (estradiol valerate 1 MG Oral Tablet) / 2 (estradiol valerate 3 MG Oral Tablet) / 2 (inert ingredients 1 MG Oral Tablet) } Pack [Natazia 28 Day] |
| 58 | http://www.nlm.nih.gov/research/umls/rxnorm | 749762 | {7 (ethinyl estradiol 0.01 MG Oral Tablet) / 84 (ethinyl estradiol 0.03 MG / levonorgestrel 0.15 MG Oral Tablet) } Pack [Seasonique] |
| 55 | http://www.nlm.nih.gov/research/umls/rxnorm | 861467 | Meperidine Hydrochloride 50 MG Oral Tablet |
| 53 | http://www.nlm.nih.gov/research/umls/rxnorm | 351136 | albuterol 0.417 MG/ML Inhalation Solution |
| 51 | http://www.nlm.nih.gov/research/umls/rxnorm | 2001499 | Vitamin B12 5 MG/ML Injectable Solution |
| 48 | http://www.nlm.nih.gov/research/umls/rxnorm | 1367439 | 21 DAY ethinyl estradiol 0.000625 MG/HR / etonogestrel 0.005 MG/HR Vaginal System [NuvaRing] |
| 45 | http://www.nlm.nih.gov/research/umls/rxnorm | 1431987 | 24 HR tacrolimus 5 MG Extended Release Oral Capsule [Astagraf] |
| 44 | http://www.nlm.nih.gov/research/umls/rxnorm | 997488 | Fexofenadine hydrochloride 30 MG Oral Tablet |
| 43 | http://www.nlm.nih.gov/research/umls/rxnorm | 665078 | Loratadine 5 MG Chewable Tablet |
| 41 | http://www.nlm.nih.gov/research/umls/rxnorm | 106258 | Hydrocortisone 10 MG/ML Topical Cream |
| 40 | http://www.nlm.nih.gov/research/umls/rxnorm | 2563431 | aspirin 81 MG Oral Capsule [Vazalore] |
| 39 | http://www.nlm.nih.gov/research/umls/rxnorm | 1648755 | nitrofurantoin, macrocrystals 25 MG / nitrofurantoin, monohydrate 75 MG Oral Capsule |
| 37 | http://www.nlm.nih.gov/research/umls/rxnorm | 243670 | aspirin 81 MG Oral Tablet |
| 37 | http://www.nlm.nih.gov/research/umls/rxnorm | 1049221 | Acetaminophen 325 MG / oxyCODONE Hydrochloride 5 MG Oral Tablet |
| 36 | http://www.nlm.nih.gov/research/umls/rxnorm | 308182 | Amoxicillin 250 MG Oral Capsule |
| 35 | http://www.nlm.nih.gov/research/umls/rxnorm | 1049630 | diphenhydrAMINE Hydrochloride 25 MG Oral Tablet |
| 33 | http://www.nlm.nih.gov/research/umls/rxnorm | 309097 | Cefuroxime 250 MG Oral Tablet |
| 31 | http://www.nlm.nih.gov/research/umls/rxnorm | 309309 | ciprofloxacin 500 MG Oral Tablet |
| 30 | http://www.nlm.nih.gov/research/umls/rxnorm | 857005 | Acetaminophen 325 MG / HYDROcodone Bitartrate 7.5 MG Oral Tablet |
| 29 | http://www.nlm.nih.gov/research/umls/rxnorm | 1534809 | 168 HR Ethinyl Estradiol 0.00146 MG/HR / norelgestromin 0.00625 MG/HR Transdermal System |
| 28 | http://www.nlm.nih.gov/research/umls/rxnorm | 855812 | prasugrel 10 MG Oral Tablet |
| 27 | http://www.nlm.nih.gov/research/umls/rxnorm | 197511 | ciprofloxacin 250 MG Oral Tablet |
| 26 | http://www.nlm.nih.gov/research/umls/rxnorm | 310436 | Galantamine 4 MG Oral Tablet |
| 23 | http://www.nlm.nih.gov/research/umls/rxnorm | 979485 | losartan potassium 25 MG Oral Tablet |
| 22 | http://www.nlm.nih.gov/research/umls/rxnorm | 197454 | cephalexin 500 MG Oral Tablet |
| 20 | http://www.nlm.nih.gov/research/umls/rxnorm | 204892 | clonazePAM 0.25 MG Oral Tablet |
| 20 | http://www.nlm.nih.gov/research/umls/rxnorm | 308971 | carbamazepine 20 MG/ML Oral Suspension [Tegretol] |
| 19 | http://www.nlm.nih.gov/research/umls/rxnorm | 477045 | Chlorpheniramine Maleate 2 MG/ML Oral Solution |
| 19 | http://www.nlm.nih.gov/research/umls/rxnorm | 235389 | Mestranol / Norethynodrel |
| 17 | http://www.nlm.nih.gov/research/umls/rxnorm | 1536144 | 120 ACTUAT mometasone furoate 0.1 MG/ACTUAT Metered Dose Inhaler [Asmanex] |
| 17 | http://www.nlm.nih.gov/research/umls/rxnorm | 1656356 | sacubitril 97 MG / valsartan 103 MG Oral Tablet [Entresto] |
| 16 | http://www.nlm.nih.gov/research/umls/rxnorm | 1804799 | Alteplase 100 MG Injection |
| 15 | http://www.nlm.nih.gov/research/umls/rxnorm | 1649987 | doxycycline hyclate 100 MG |
| 15 | http://www.nlm.nih.gov/research/umls/rxnorm | 241834 | cycloSPORINE, modified 100 MG Oral Capsule |
| 15 | http://www.nlm.nih.gov/research/umls/rxnorm | 198335 | sulfamethoxazole 800 MG / trimethoprim 160 MG Oral Tablet |
| 14 | http://www.nlm.nih.gov/research/umls/rxnorm | 243670 | Aspirin 81 MG Oral Tablet |
| 14 | http://www.nlm.nih.gov/research/umls/rxnorm | 1599803 | 24 HR Donepezil hydrochloride 10 MG / Memantine hydrochloride 28 MG Extended Release Oral Capsule |
| 13 | http://www.nlm.nih.gov/research/umls/rxnorm | 197591 | Diazepam 5 MG Oral Tablet |
| 13 | http://www.nlm.nih.gov/research/umls/rxnorm | 1014676 | cetirizine hydrochloride 5 MG Oral Tablet |
| 13 | http://www.nlm.nih.gov/research/umls/rxnorm | 197378 | Astemizole 10 MG Oral Tablet |
| 13 | http://www.nlm.nih.gov/research/umls/rxnorm | 284988 | didanosine 400 MG Delayed Release Oral Capsule |
| 12 | http://www.nlm.nih.gov/research/umls/rxnorm | 749882 | {7 (inert ingredients 1 MG Oral Tablet) / 21 (mestranol 0.05 MG / norethindrone 1 MG Oral Tablet) } Pack [Norinyl 1+50 28 Day] |
| 11 | http://www.nlm.nih.gov/research/umls/rxnorm | 617296 | amoxicillin 500 MG / clavulanate 125 MG Oral Tablet |
| 9 | http://www.nlm.nih.gov/research/umls/rxnorm | 617311 | atorvastatin 40 MG Oral Tablet |
| 8 | http://www.nlm.nih.gov/research/umls/rxnorm | 855332 | warfarin sodium 5 MG Oral Tablet |
| 8 | http://www.nlm.nih.gov/research/umls/rxnorm | 198014 | Naproxen 500 MG Oral Tablet |
| 8 | http://www.nlm.nih.gov/research/umls/rxnorm | 749785 | {7 (ethinyl estradiol 0.035 MG / norgestimate 0.18 MG Oral Tablet) / 7 (ethinyl estradiol 0.035 MG / norgestimate 0.215 MG Oral Tablet) / 7 (ethinyl estradiol 0.035 MG / norgestimate 0.25 MG Oral Tablet) / 7 (inert ingredients 1 MG Oral Tablet) } Pack [Ortho Tri-Cyclen 28 Day] |
| 8 | http://www.nlm.nih.gov/research/umls/rxnorm | 198031 | 24 HR nicotine 0.292 MG/HR Transdermal System |
| 7 | http://www.nlm.nih.gov/research/umls/rxnorm | 312938 | Sertraline 100 MG Oral Tablet |
| 7 | http://www.nlm.nih.gov/research/umls/rxnorm | 896006 | 120 ACTUAT fluticasone propionate 0.22 MG/ACTUAT Metered Dose Inhaler [Flovent] |
| 7 | http://www.nlm.nih.gov/research/umls/rxnorm | 313110 | stavudine 40 MG Oral Capsule |
| 7 | http://www.nlm.nih.gov/research/umls/rxnorm | 310988 | indinavir 400 MG Oral Capsule |
| 6 | http://www.nlm.nih.gov/research/umls/rxnorm | 866924 | metoprolol tartrate 25 MG Oral Tablet |
| 6 | http://www.nlm.nih.gov/research/umls/rxnorm | 1648756 | nitrofurantoin, macrocrystals 25 MG / nitrofurantoin, monohydrate 75 MG [Macrobid] |
| 6 | http://www.nlm.nih.gov/research/umls/rxnorm | 197319 | Allopurinol 100 MG Oral Tablet |
| 6 | http://www.nlm.nih.gov/research/umls/rxnorm | 966222 | Levothyroxine Sodium 0.075 MG Oral Tablet |
| 6 | http://www.nlm.nih.gov/research/umls/rxnorm | 312615 | predniSONE 20 MG Oral Tablet |
| 6 | http://www.nlm.nih.gov/research/umls/rxnorm | 476556 | emtricitabine 200 MG / tenofovir disoproxil fumarate 300 MG Oral Tablet |
| 5 | http://www.nlm.nih.gov/research/umls/rxnorm | 1091392 | Methylphenidate Hydrochloride 20 MG Oral Tablet |
| 5 | http://www.nlm.nih.gov/research/umls/rxnorm | 979480 | losartan potassium 100 MG Oral Tablet |
| 5 | http://www.nlm.nih.gov/research/umls/rxnorm | 311372 | Loratadine 10 MG Oral Tablet |
| 5 | http://www.nlm.nih.gov/research/umls/rxnorm | 1359133 | {5 (ethinyl estradiol 0.02 MG / norethindrone acetate 1 MG Oral Tablet) / 7 (ethinyl estradiol 0.03 MG / norethindrone acetate 1 MG Oral Tablet) / 9 (ethinyl estradiol 0.035 MG / norethindrone acetate 1 MG Oral Tablet) / 7 (ferrous fumarate 75 MG Oral Tablet) } Pack [Estrostep Fe 28 Day] |
| 5 | http://www.nlm.nih.gov/research/umls/rxnorm | 617312 | atorvastatin 10 MG Oral Tablet |
| 4 | http://www.nlm.nih.gov/research/umls/rxnorm | 313185 | Tacrine 10 MG Oral Capsule |
| 4 | http://www.nlm.nih.gov/research/umls/rxnorm | 608139 | atomoxetine 100 MG Oral Capsule |
| 4 | http://www.nlm.nih.gov/research/umls/rxnorm | 1100184 | Donepezil hydrochloride 23 MG Oral Tablet |
| 4 | http://www.nlm.nih.gov/research/umls/rxnorm | 562508 | amoxicillin 875 MG / clavulanate 125 MG Oral Tablet |
| 4 | http://www.nlm.nih.gov/research/umls/rxnorm | 197884 | lisinopril 40 MG Oral Tablet |
| 4 | http://www.nlm.nih.gov/research/umls/rxnorm | 856980 | acetaminophen 300 MG / hydrocodone bitartrate 10 MG Oral Tablet |
| 4 | http://www.nlm.nih.gov/research/umls/rxnorm | 141918 | Terfenadine 60 MG Oral Tablet |
| 4 | http://www.nlm.nih.gov/research/umls/rxnorm | 259255 | atorvastatin 80 MG Oral Tablet |
| 4 | http://www.nlm.nih.gov/research/umls/rxnorm | 313002 | Sodium Chloride 9 MG/ML Injectable Solution |
| 4 | http://www.nlm.nih.gov/research/umls/rxnorm | 199663 | zidovudine 300 MG Oral Tablet |
| 4 | http://www.nlm.nih.gov/research/umls/rxnorm | 349477 | efavirenz 600 MG Oral Tablet |
| 3 | http://www.nlm.nih.gov/research/umls/rxnorm | 284215 | clindamycin 300 MG Oral Capsule |
| 3 | http://www.nlm.nih.gov/research/umls/rxnorm | 686924 | carvedilol 3.125 MG Oral Tablet |
| 3 | http://www.nlm.nih.gov/research/umls/rxnorm | 904467 | pravastatin sodium 20 MG Oral Tablet |
| 3 | http://www.nlm.nih.gov/research/umls/rxnorm | 996740 | Memantine hydrochloride 2 MG/ML Oral Solution |
| 3 | http://www.nlm.nih.gov/research/umls/rxnorm | 1014678 | cetirizine hydrochloride 10 MG Oral Tablet |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 997501 | Fexofenadine hydrochloride 60 MG Oral Tablet |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 617310 | atorvastatin 20 MG Oral Tablet |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 197380 | atenolol 25 MG Oral Tablet |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 979464 | hydrochlorothiazide 12.5 MG / losartan potassium 100 MG Oral Tablet |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 313760 | zalcitabine 0.75 MG Oral Tablet |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 200031 | carvedilol 6.25 MG Oral Tablet |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 314231 | simvastatin 10 MG Oral Tablet |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 310385 | FLUoxetine 20 MG Oral Capsule |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 664741 | atazanavir 300 MG Oral Capsule |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 317150 | ritonavir 100 MG Oral Capsule |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 866427 | 24 HR metoprolol succinate 25 MG Extended Release Oral Tablet |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 866436 | 24 HR metoprolol succinate 50 MG Extended Release Oral Tablet |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 198211 | simvastatin 40 MG Oral Tablet |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 979468 | hydrochlorothiazide 12.5 MG / losartan potassium 50 MG Oral Tablet |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 105078 | Penicillin G 375 MG/ML Injectable Solution |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 483438 | pregabalin 100 MG Oral Capsule |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 997223 | Donepezil hydrochloride 10 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 205326 | lisinopril 30 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 476350 | ezetimibe 10 MG / simvastatin 40 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 859751 | rosuvastatin calcium 20 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 751623 | nebivolol 5 MG Oral Tablet [Bystolic] |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 854905 | bisoprolol fumarate 5 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 200096 | irbesartan 300 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 197541 | Colchicine 0.6 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 859749 | rosuvastatin calcium 10 MG Oral Tablet [Crestor] |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 859424 | rosuvastatin calcium 5 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 854916 | bisoprolol fumarate 2.5 MG / hydrochlorothiazide 6.25 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 898723 | benazepril hydrochloride 5 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 866511 | metoprolol tartrate 100 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 854901 | bisoprolol fumarate 10 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 197904 | lovastatin 20 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 898687 | benazepril hydrochloride 10 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 866514 | metoprolol tartrate 50 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 789980 | Ampicillin 100 MG/ML Injectable Solution |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 1363309 | Chlorpheniramine Maleate 4 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 856457 | propranolol hydrochloride 20 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 312961 | simvastatin 20 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 311354 | lisinopril 5 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 349199 | valsartan 80 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 856519 | propranolol hydrochloride 40 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 856448 | propranolol hydrochloride 10 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 904458 | pravastatin sodium 10 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 141962 | Azithromycin 250 MG Oral Capsule |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 904481 | pravastatin sodium 80 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 197905 | lovastatin 40 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 808917 | fosfomycin 3000 MG Granules for Oral Solution |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 105585 | Methotrexate 2.5 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 833135 | Milnacipran hydrochloride 100 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 904475 | pravastatin sodium 40 MG Oral Tablet |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 200345 | simvastatin 80 MG Oral Tablet |

### AllergyIntolerance (22 distinct codes)

| Count | System | Code | Display |
|---|---|---|---|
| 208 | http://snomed.info/sct | 609328004 | Allergic disposition (finding) |
| 120 | http://snomed.info/sct | 84489001 | Mold (organism) |
| 113 | http://snomed.info/sct | 264287008 | Animal dander (substance) |
| 92 | http://snomed.info/sct | 260147004 | House dust mite (organism) |
| 91 | http://snomed.info/sct | 782576004 | Tree pollen (substance) |
| 87 | http://snomed.info/sct | 256277009 | Grass pollen (substance) |
| 48 | http://snomed.info/sct | 735029006 | Shellfish (substance) |
| 46 | http://www.nlm.nih.gov/research/umls/rxnorm | 1191 | Aspirin |
| 42 | http://snomed.info/sct | 762952008 | Peanut (substance) |
| 37 | http://snomed.info/sct | 102263004 | Eggs (edible) (substance) |
| 37 | http://snomed.info/sct | 111088007 | Latex (substance) |
| 36 | http://snomed.info/sct | 288328004 | Bee venom (substance) |
| 31 | http://snomed.info/sct | 735971005 | Fish (substance) |
| 30 | http://snomed.info/sct | 412071004 | Wheat (substance) |
| 28 | http://www.nlm.nih.gov/research/umls/rxnorm | 29046 | Lisinopril |
| 26 | http://www.nlm.nih.gov/research/umls/rxnorm | 7984 | Penicillin V |
| 26 | http://snomed.info/sct | 3718001 | Cow's milk (substance) |
| 23 | http://snomed.info/sct | 442571000124108 | Tree nut (substance) |
| 15 | http://snomed.info/sct | 256355007 | Glycine max (substance) |
| 11 | http://www.nlm.nih.gov/research/umls/rxnorm | 10831 | Sulfamethoxazole / Trimethoprim |
| 2 | http://www.nlm.nih.gov/research/umls/rxnorm | 5640 | Ibuprofen |
| 1 | http://www.nlm.nih.gov/research/umls/rxnorm | 25037 | cefdinir |

### DiagnosticReport (37 distinct codes)

| Count | System | Code | Display |
|---|---|---|---|
| 73448 | http://loinc.org | 34117-2 | History and physical note |
| 73448 | http://loinc.org | 51847-2 | Evaluation + Plan note |
| 10075 | http://loinc.org | 55757-9 | Patient Health Questionnaire 2 item (PHQ-2) [Reported] |
| 9281 | http://loinc.org | 24357-6 | Urinalysis macro (dipstick) panel - Urine |
| 9016 | http://loinc.org | 51990-0 | Basic metabolic panel - Blood |
| 7717 | http://loinc.org | 57698-3 | Lipid panel with direct LDL - Serum or Plasma |
| 6955 | http://loinc.org | 24321-2 | Basic metabolic 2000 panel - Serum or Plasma |
| 6695 | http://loinc.org | 69737-5 | Generalized anxiety disorder 7 item (GAD-7) |
| 4275 | http://loinc.org | 24323-8 | Comprehensive metabolic 2000 panel - Serum or Plasma |
| 4180 | http://loinc.org | 58410-2 | CBC panel - Blood by Automated count |
| 3901 | http://loinc.org | 82666-9 | Drug Abuse Screening Test-10 [DAST-10] |
| 3791 | http://loinc.org | 76499-3 | Humiliation, Afraid, Rape, and Kick questionnaire [HARK] |
| 3781 | http://loinc.org | 72109-2 | Alcohol Use Disorder Identification Test - Consumption [AUDIT-C] |
| 3172 | http://loinc.org | 59453-1 | Morse Fall Scale panel |
| 692 | http://loinc.org | 89206-7 | Patient Health Questionnaire-9: Modified for Teens [Reported.PHQ.Teen] |
| 625 | http://loinc.org | 89577-1 | Troponin I.cardiac panel - Serum or Plasma by High sensitivity method |
| 582 | http://loinc.org | 44249-1 | PHQ-9 quick depression assessment panel [Reported.PHQ] |
| 579 | http://loinc.org | 75689-0 | Iron panel - Serum or Plasma |
| 538 | http://loinc.org | 87674-8 | Optical coherence tomography study |
| 511 | http://loinc.org | 50190-8 | Iron and Iron binding capacity panel - Serum or Plasma |
| 460 | http://loinc.org | 24336-0 | Gas panel - Arterial blood |
| 404 | http://loinc.org | 34528-0 | PT panel - Platelet poor plasma by Coagulation assay |
| 312 | http://loinc.org | 51990-0 | Basic Metabolic Panel - Blood |
| 200 | http://loinc.org | 55405-5 | Heart failure tracking panel |
| 198 | http://loinc.org | 24356-8 | Urinalysis complete panel - Urine |
| 168 | http://loinc.org | 69409-1 | U.S. standard certificate of death - 2003 revision |
| 158 | http://loinc.org | 57023-4 | Auto Differential panel - Blood |
| 115 | http://loinc.org | 94531-1 | SARS-CoV-2 (COVID-19) RNA panel - Respiratory system specimen by NAA with probe detection |
| 64 | http://loinc.org | 24321-2 | Basic Metabolic 2000 Panel - Serum or Plasma |
| 55 | http://loinc.org | 92143-7 | Respiratory pathogens DNA and RNA panel - Respiratory system specimen by NAA with probe detection |
| 54 | http://loinc.org | 24339-4 | Gas panel - Venous blood |
| 46 | http://loinc.org | 80381-7 | Influenza virus A and B Ag panel - Upper respiratory specimen by Rapid immunoassay |
| 38 | http://loinc.org | 93124-6 | New York Heart Association Functional Classification panel |
| 13 | http://loinc.org | 600-7 | Bacteria identified in Blood by Culture |
| 8 | http://loinc.org | 24360-0 | Hemoglobin and Hematocrit panel - Blood |
| 4 | http://loinc.org | 69742-5 | CBC W Differential panel, method unspecified - Blood |
| 1 | http://loinc.org | 75622-1 | HIV 1 and 2 tests - Meaningful Use set |

### Immunization (21 distinct codes)

| Count | System | Code | Display |
|---|---|---|---|
| 9494 | http://hl7.org/fhir/sid/cvx | 140 | Influenza, split virus, trivalent, PF |
| 896 | http://hl7.org/fhir/sid/cvx | 113 | Td (adult), 5 Lf tetanus toxoid, preservative free, adsorbed |
| 798 | http://hl7.org/fhir/sid/cvx | 208 | COVID-19, mRNA, LNP-S, PF, 30 mcg/0.3 mL dose |
| 581 | http://hl7.org/fhir/sid/cvx | 207 | COVID-19, mRNA, LNP-S, PF, 100 mcg/0.5mL dose or 50 mcg/0.25mL dose |
| 556 | http://hl7.org/fhir/sid/cvx | 133 | Pneumococcal conjugate PCV 13 |
| 547 | http://hl7.org/fhir/sid/cvx | 20 | DTaP |
| 468 | http://hl7.org/fhir/sid/cvx | 10 | IPV |
| 386 | http://hl7.org/fhir/sid/cvx | 114 | meningococcal MCV4P |
| 374 | http://hl7.org/fhir/sid/cvx | 62 | HPV, quadrivalent |
| 334 | http://hl7.org/fhir/sid/cvx | 49 | Hib (PRP-OMP) |
| 333 | http://hl7.org/fhir/sid/cvx | 08 | Hep B, adolescent or pediatric |
| 330 | http://hl7.org/fhir/sid/cvx | 52 | Hep A, adult |
| 320 | http://hl7.org/fhir/sid/cvx | 121 | zoster vaccine, live |
| 229 | http://hl7.org/fhir/sid/cvx | 03 | MMR |
| 225 | http://hl7.org/fhir/sid/cvx | 21 | varicella |
| 223 | http://hl7.org/fhir/sid/cvx | 43 | Hep B, adult |
| 215 | http://hl7.org/fhir/sid/cvx | 119 | rotavirus, monovalent |
| 211 | http://hl7.org/fhir/sid/cvx | 83 | Hep A, ped/adol, 2 dose |
| 125 | http://hl7.org/fhir/sid/cvx | 115 | Tdap |
| 125 | http://hl7.org/fhir/sid/cvx | 33 | pneumococcal polysaccharide vaccine, 23 valent |
| 48 | http://hl7.org/fhir/sid/cvx | 212 | COVID-19 vaccine, vector-nr, rS-Ad26, PF, 0.5 mL |

### Observation (281 distinct codes)

| Count | System | Code | Display |
|---|---|---|---|
| 31872 | http://loinc.org | 72514-3 | Pain severity - 0-10 verbal numeric rating [Score] - Reported |
| 17725 | http://loinc.org | 8462-4 | Diastolic Blood Pressure |
| 17725 | http://loinc.org | 8480-6 | Systolic Blood Pressure |
| 17672 | http://loinc.org | 85354-9 | Blood pressure panel with all children optional |
| 17108 | http://loinc.org | 29463-7 | Body Weight |
| 16582 | http://loinc.org | 8867-4 | Heart rate |
| 16582 | http://loinc.org | 9279-1 | Respiratory rate |
| 16377 | http://loinc.org | 8302-2 | Body Height |
| 16309 | http://loinc.org | 72166-2 | Tobacco smoking status |
| 15294 | http://loinc.org | 39156-5 | Body mass index (BMI) [Ratio] |
| 15106 | http://loinc.org | 33914-3 | Glomerular filtration rate [Volume Rate/Area] in Serum or Plasma by Creatinine-based formula (MDRD)/1.73 sq M |
| 12888 | http://loinc.org | 71802-3 | Housing status |
| 12832 | http://loinc.org | 93025-5 | Protocol for Responding to and Assessing Patients' Assets, Risks, and Experiences [PRAPARE] |
| 12832 | http://loinc.org | 76501-6 | Within the last year, have you been afraid of your partner or ex-partner |
| 12832 | http://loinc.org | 93026-3 | Do you feel physically and emotionally safe where you currently live [PRAPARE] |
| 12832 | http://loinc.org | 93027-1 | Are you a refugee |
| 12832 | http://loinc.org | 93028-9 | Have you spent more than 2 nights in a row in a jail, prison, detention center, or juvenile correctional facility in past 1 year [PRAPARE] |
| 12832 | http://loinc.org | 93038-8 | Stress level |
| 12832 | http://loinc.org | 93029-7 | How often do you see or talk to people that you care about and feel close to [PRAPARE] |
| 12832 | http://loinc.org | 93030-5 | Has lack of transportation kept you from medical appointments, meetings, work, or from getting things needed for daily living |
| 12832 | http://loinc.org | 93031-3 | Have you or any family members you live with been unable to get any of the following when it was really needed in past 1 year [PRAPARE] |
| 12832 | http://loinc.org | 63586-2 | What was your best estimate of the total income of all family members from all sources, before taxes, in last year [PhenX] |
| 12832 | http://loinc.org | 76437-3 | Primary insurance |
| 12832 | http://loinc.org | 67875-5 | Employment status - current |
| 12832 | http://loinc.org | 82589-3 | Highest level of education |
| 12832 | http://loinc.org | 56799-0 | Address |
| 12832 | http://loinc.org | 93033-9 | Are you worried about losing your housing [PRAPARE] |
| 12832 | http://loinc.org | 63512-8 | How many people are living or staying at this address [#] |
| 12832 | http://loinc.org | 54899-0 | Preferred language |
| 12832 | http://loinc.org | 93034-7 | Discharged from the U.S. Armed Forces |
| 12832 | http://loinc.org | 93035-4 | Has season or migrant farm work been your or your family's main source of income at any point in past 2 years [PRAPARE] |
| 12832 | http://loinc.org | 32624-9 | Race |
| 12832 | http://loinc.org | 56051-6 | Hispanic or Latino |
| 12623 | http://loinc.org | 2339-0 | Glucose [Mass/volume] in Blood |
| 12623 | http://loinc.org | 38483-4 | Creatinine [Mass/volume] in Blood |
| 12623 | http://loinc.org | 49765-1 | Calcium [Mass/volume] in Blood |
| 12623 | http://loinc.org | 2947-0 | Sodium [Moles/volume] in Blood |
| 12623 | http://loinc.org | 6298-4 | Potassium [Moles/volume] in Blood |
| 12623 | http://loinc.org | 2069-3 | Chloride [Moles/volume] in Blood |
| 12623 | http://loinc.org | 20565-8 | Carbon dioxide, total [Moles/volume] in Blood |
| 12475 | http://loinc.org | 74006-8 | Weight difference [Mass difference] --pre dialysis - post dialysis |
| 12247 | http://loinc.org | 6299-2 | Urea nitrogen [Mass/volume] in Blood |
| 11701 | http://loinc.org | 4548-4 | Hemoglobin A1c/Hemoglobin.total in Blood |
| 10075 | http://loinc.org | 55758-7 | Patient Health Questionnaire 2 item (PHQ-2) total score [Reported] |
| 9479 | http://loinc.org | 2514-8 | Ketones [Presence] in Urine by Test strip |
| 9479 | http://loinc.org | 5811-5 | Specific gravity of Urine by Test strip |
| 9479 | http://loinc.org | 5803-2 | pH of Urine by Test strip |
| 9479 | http://loinc.org | 5802-4 | Nitrite [Presence] in Urine by Test strip |
| 9479 | http://loinc.org | 5794-3 | Hemoglobin [Presence] in Urine by Test strip |
| 9479 | http://loinc.org | 5799-2 | Leukocyte esterase [Presence] in Urine by Test strip |
| 9336 | http://loinc.org | 25428-4 | Glucose [Presence] in Urine by Test strip |
| 9336 | http://loinc.org | 5770-3 | Bilirubin.total [Presence] in Urine by Test strip |
| 9336 | http://loinc.org | 20454-5 | Protein [Presence] in Urine by Test strip |
| 9281 | http://loinc.org | 5792-7 | Glucose [Mass/volume] in Urine by Test strip |
| 9281 | http://loinc.org | 5804-0 | Protein [Mass/volume] in Urine by Test strip |
| 9202 | http://loinc.org | 5767-9 | Appearance of Urine |
| 9138 | http://loinc.org | 32167-9 | Clarity of Urine |
| 9138 | http://loinc.org | 5778-6 | Color of Urine |
| 9138 | http://loinc.org | 20505-4 | Bilirubin.total [Mass/volume] in Urine by Test strip |
| 9138 | http://loinc.org | 5797-6 | Ketones [Mass/volume] in Urine by Test strip |
| 9074 | http://loinc.org | 34533-0 | Odor of Urine |
| 7999 | http://loinc.org | 2345-7 | Glucose [Mass/volume] in Serum or Plasma |
| 7999 | http://loinc.org | 3094-0 | Urea nitrogen [Mass/volume] in Serum or Plasma |
| 7999 | http://loinc.org | 2160-0 | Creatinine [Mass/volume] in Serum or Plasma |
| 7999 | http://loinc.org | 17861-6 | Calcium [Mass/volume] in Serum or Plasma |
| 7999 | http://loinc.org | 2951-2 | Sodium [Moles/volume] in Serum or Plasma |
| 7999 | http://loinc.org | 2823-3 | Potassium [Moles/volume] in Serum or Plasma |
| 7999 | http://loinc.org | 2075-0 | Chloride [Moles/volume] in Serum or Plasma |
| 7999 | http://loinc.org | 2028-9 | Carbon dioxide, total [Moles/volume] in Serum or Plasma |
| 7717 | http://loinc.org | 2093-3 | Cholesterol [Mass/volume] in Serum or Plasma |
| 7717 | http://loinc.org | 2571-8 | Triglyceride [Mass/volume] in Serum or Plasma |
| 7717 | http://loinc.org | 18262-6 | Cholesterol in LDL [Mass/volume] in Serum or Plasma by Direct assay |
| 7717 | http://loinc.org | 2085-9 | Cholesterol in HDL [Mass/volume] in Serum or Plasma |
| 6695 | http://loinc.org | 70274-6 | Generalized anxiety disorder 7 item (GAD-7) total score [Reported.PHQ] |
| 4275 | http://loinc.org | 2885-2 | Protein [Mass/volume] in Serum or Plasma |
| 4275 | http://loinc.org | 1751-7 | Albumin [Mass/volume] in Serum or Plasma |
| 4275 | http://loinc.org | 6768-6 | Alkaline phosphatase [Enzymatic activity/volume] in Serum or Plasma |
| 4275 | http://loinc.org | 1742-6 | Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma |
| 4275 | http://loinc.org | 1920-8 | Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma |
| 4271 | http://loinc.org | 1975-2 | Bilirubin.total [Mass/volume] in Serum or Plasma |
| 4192 | http://loinc.org | 718-7 | Hemoglobin [Mass/volume] in Blood |
| 4180 | http://loinc.org | 6690-2 | Leukocytes [#/volume] in Blood by Automated count |
| 4180 | http://loinc.org | 789-8 | Erythrocytes [#/volume] in Blood by Automated count |
| 4180 | http://loinc.org | 787-2 | MCV [Entitic mean volume] in Red Blood Cells by Automated count |
| 4180 | http://loinc.org | 785-6 | MCH [Entitic mass] by Automated count |
| 4180 | http://loinc.org | 786-4 | MCHC [Entitic Mass/volume] in Red Blood Cells by Automated count |
| 4180 | http://loinc.org | 788-0 | Erythrocyte [DistWidth] in Blood by Automated count |
| 4180 | http://loinc.org | 777-3 | Platelets [#/volume] in Blood by Automated count |
| 4057 | http://loinc.org | 4544-3 | Hematocrit [Volume Fraction] of Blood by Automated count |
| 3901 | http://loinc.org | 82667-7 | Total score [DAST-10] |
| 3816 | http://loinc.org | 14959-1 | Microalbumin/Creatinine [Mass Ratio] in Urine |
| 3791 | http://loinc.org | 76504-0 | Total score [HARK] |
| 3781 | http://loinc.org | 75626-2 | Total score [AUDIT-C] |
| 3235 | http://loinc.org | 10834-0 | Globulin [Mass/volume] in Serum by calculation |
| 3172 | http://loinc.org | 59460-6 | Fall risk total [Morse Fall Scale] |
| 3172 | http://loinc.org | 59461-4 | Fall risk level [Morse Fall Scale] |
| 3144 | http://loinc.org | 32207-3 | Platelet distribution width [Entitic volume] in Blood by Automated count |
| 3144 | http://loinc.org | 32623-1 | Platelet [Entitic mean volume] in Blood by Automated count |
| 2665 | http://loinc.org | 59576-9 | Body mass index (BMI) [Percentile] Per age and sex |
| 2084 | http://loinc.org | 41633001 | Intraocular pressure (observable entity) |
| 1579 | http://loinc.org | 77606-2 | Weight-for-length Per age and sex |
| 1579 | http://loinc.org | 8289-1 | Head Occipital-frontal circumference Percentile |
| 1579 | http://loinc.org | 9843-4 | Head Occipital-frontal circumference |
| 1224 | http://loinc.org | 2708-6 | Oxygen saturation in Arterial blood |
| 1224 | http://loinc.org | 59408-5 | Oxygen saturation in Arterial blood by Pulse oximetry |
| 1107 | http://loinc.org | 8310-5 | Body temperature |
| 1107 | http://loinc.org | 8331-1 | Oral temperature |
| 1042 | http://snomed.info/sct | 413077008 | LogMAR visual acuity left eye (observable entity) |
| 1042 | http://loinc.org | 98498-9 | Visual acuity uncorrected Left eye |
| 1042 | http://snomed.info/sct | 413078003 | LogMAR visual acuity right eye (observable entity) |
| 1042 | http://loinc.org | 98499-7 | Visual acuity uncorrected Right eye |
| 1042 | http://loinc.org | 79893-4 | Left eye Intraocular pressure |
| 1042 | http://loinc.org | 79892-6 | Right eye Intraocular pressure |
| 1042 | http://loinc.org | 71490-7 | Left eye Diabetic retinopathy severity level by Ophthalmoscopy |
| 1042 | http://loinc.org | 71491-5 | Right eye Diabetic retinopathy severity level by Ophthalmoscopy |
| 938 | http://loinc.org | 19123-9 | Magnesium [Mass/volume] in Serum or Plasma |
| 692 | http://loinc.org | 89204-2 | Patient Health Questionnaire-9: Modified for Teens total score [Reported.PHQ.Teen] |
| 665 | http://loinc.org | 89579-7 | Troponin I.cardiac [Mass/volume] in Serum or Plasma by High sensitivity method |
| 630 | http://loinc.org | 19926-5 | FEV1/FVC |
| 582 | http://loinc.org | 44261-6 | Patient Health Questionnaire 9 item (PHQ-9) total score [Reported] |
| 579 | http://loinc.org | 2276-4 | Ferritin [Mass/volume] in Serum or Plasma |
| 538 | http://loinc.org | 79819-9 | Study observation Left retina by OCT |
| 538 | http://loinc.org | 79818-1 | Study observation Right retina by OCT |
| 511 | http://loinc.org | 33762-6 | Natriuretic peptide.B prohormone N-Terminal [Mass/volume] in Serum or Plasma |
| 511 | http://loinc.org | 2498-4 | Iron [Mass/volume] in Serum or Plasma |
| 511 | http://loinc.org | 2500-7 | Iron binding capacity [Mass/volume] in Serum or Plasma |
| 511 | http://loinc.org | 2502-3 | Iron saturation [Mass Fraction] in Serum or Plasma |
| 474 | http://loinc.org | 6301-6 | INR in Platelet poor plasma by Coagulation assay |
| 460 | http://loinc.org | 2744-1 | pH of Arterial blood |
| 460 | http://loinc.org | 2019-8 | Carbon dioxide [Partial pressure] in Arterial blood |
| 460 | http://loinc.org | 2703-7 | Oxygen [Partial pressure] in Arterial blood |
| 460 | http://loinc.org | 1960-4 | Bicarbonate [Moles/volume] in Arterial blood |
| 441 | http://loinc.org | 82810-3 | Pregnancy status |
| 404 | http://loinc.org | 5902-2 | Prothrombin time (PT) |
| 376 | http://loinc.org | 6299-2 | Urea Nitrogen [Mass/volume] in Blood |
| 369 | http://loinc.org | 3173-2 | aPTT in Blood by Coagulation assay |
| 336 | http://loinc.org | 2777-1 | Phosphate [Mass/volume] in Serum or Plasma |
| 278 | http://loinc.org | 38208-5 | Pain severity - Reported |
| 200 | http://loinc.org | 10230-1 | Left ventricular Ejection fraction |
| 198 | http://loinc.org | 75325-1 | Symptom |
| 168 | http://loinc.org | 69453-9 | Cause of Death [US Standard Certificate of Death] |
| 158 | http://loinc.org | 770-8 | Neutrophils/Leukocytes in Blood by Automated count |
| 158 | http://loinc.org | 736-9 | Lymphocytes/Leukocytes in Blood by Automated count |
| 158 | http://loinc.org | 5905-5 | Monocytes/Leukocytes in Blood by Automated count |
| 158 | http://loinc.org | 713-8 | Eosinophils/Leukocytes in Blood by Automated count |
| 158 | http://loinc.org | 706-2 | Basophils/Leukocytes in Blood by Automated count |
| 158 | http://loinc.org | 751-8 | Neutrophils [#/volume] in Blood by Automated count |
| 158 | http://loinc.org | 731-0 | Lymphocytes [#/volume] in Blood by Automated count |
| 158 | http://loinc.org | 742-7 | Monocytes [#/volume] in Blood by Automated count |
| 158 | http://loinc.org | 711-2 | Eosinophils [#/volume] in Blood by Automated count |
| 158 | http://loinc.org | 704-7 | Basophils [#/volume] in Blood by Automated count |
| 143 | http://loinc.org | 5821-4 | Leukocytes [#/area] in Urine sediment by Microscopy high power field |
| 143 | http://loinc.org | 13945-1 | Erythrocytes [#/area] in Urine sediment by Microscopy high power field |
| 143 | http://loinc.org | 5787-7 | Epithelial cells [#/area] in Urine sediment by Microscopy high power field |
| 143 | http://loinc.org | 24124-0 | Casts [Presence] in Urine sediment by Light microscopy |
| 143 | http://loinc.org | 8247-9 | Mucus [Presence] in Urine sediment by Light microscopy |
| 143 | http://loinc.org | 5769-5 | Bacteria [#/area] in Urine sediment by Microscopy high power field |
| 143 | http://loinc.org | 630-4 | Bacteria identified in Urine by Culture |
| 138 | http://loinc.org | 91148-7 | Pain intensity, Enjoyment of life, General activity scale [PEG] |
| 138 | http://loinc.org | 91146-1 | What number best describes how pain has interfered with your general activity during the past week |
| 138 | http://loinc.org | 91145-3 | What number best describes how pain has interfered with your enjoyment of life during the past week |
| 138 | http://loinc.org | 75893-8 | Pain severity in the past week - 0-10 numeric rating [Reported] |
| 135 | http://loinc.org | 20570-8 | Hematocrit [Volume Fraction] of Blood by calculation |
| 117 | http://loinc.org | X9999-0 | Operative Status |
| 117 | http://loinc.org | X9999-2 | Priority Level |
| 117 | http://loinc.org | X9999-1 | Operative Status Value |
| 115 | http://loinc.org | 94531-1 | SARS-CoV-2 (COVID-19) RNA panel - Respiratory system specimen by NAA with probe detection |
| 108 | http://loinc.org | 29554-3 | Procedure Narrative |
| 105 | http://loinc.org | 38265-5 | DXA Radius and Ulna [T-score] Bone density |
| 100 | http://loinc.org | 33756-8 | Polyp size greatest dimension |
| 100 | http://loinc.org | 57905-2 | Hemoglobin.gastrointestinal.lower [Presence] in Stool by Immunoassay --1st specimen |
| 91 | http://loinc.org | 72106-8 | Total score [MMSE] |
| 89 | http://loinc.org | 6206-7 | Peanut IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 6273-7 | Walnut IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 6082-2 | Codfish IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 6246-3 | Shrimp IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 6276-0 | Wheat IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 6106-9 | Egg white IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 6248-9 | Soybean IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 7258-7 | Cow milk IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 6189-5 | White oak IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 6085-5 | Common Ragweed IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 6833-8 | Cat dander IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 6095-4 | American house dust mite IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 6075-6 | Cladosporium herbarum IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 6844-5 | Honey bee IgE Ab [Units/volume] in Serum |
| 89 | http://loinc.org | 6158-0 | Latex IgE Ab [Units/volume] in Serum |
| 82 | http://loinc.org | 65750-2 | Drugs of abuse 5 panel - Urine by Screen method |
| 71 | http://loinc.org | 32465-7 | Physical findings of Prostate |
| 71 | http://loinc.org | 2857-1 | Prostate specific Ag [Mass/volume] in Serum or Plasma |
| 70 | http://loinc.org | 19994-3 | Oxygen/Total gas setting [Volume Fraction] Ventilator |
| 68 | http://loinc.org | 48065-7 | Fibrin D-dimer FEU [Mass/volume] in Platelet poor plasma |
| 68 | http://loinc.org | 14804-9 | Lactate dehydrogenase [Enzymatic activity/volume] in Serum or Plasma by Lactate to pyruvate reaction |
| 68 | http://loinc.org | 2532-0 | Lactate dehydrogenase [Enzymatic activity/volume] in Serum or Plasma |
| 68 | http://loinc.org | 2157-6 | Creatine kinase [Enzymatic activity/volume] in Serum or Plasma |
| 68 | http://loinc.org | 1988-5 | C reactive protein [Mass/volume] in Serum or Plasma |
| 68 | http://loinc.org | 33959-8 | Procalcitonin [Mass/volume] in Serum or Plasma |
| 59 | http://loinc.org | 3184-9 | Activated clotting time (ACT) of Blood by Coagulation assay |
| 56 | http://loinc.org | 76690-7 | Sexual orientation |
| 56 | http://loinc.org | 55277-8 | HIV status |
| 56 | http://loinc.org | 28245-9 | Abuse Status [OMAHA] |
| 56 | http://loinc.org | 63513-6 | Are you covered by health insurance or some other kind of health care plan [PhenX] |
| 56 | http://loinc.org | 46240-8 | History of Hospitalizations+Outpatient visits Narrative |
| 55 | http://loinc.org | 92142-9 | Influenza virus A RNA [Presence] in Respiratory system specimen by NAA with probe detection |
| 55 | http://loinc.org | 92141-1 | Influenza virus B RNA [Presence] in Respiratory system specimen by NAA with probe detection |
| 55 | http://loinc.org | 92131-2 | Respiratory syncytial virus RNA [Presence] in Respiratory system specimen by NAA with probe detection |
| 55 | http://loinc.org | 92140-3 | Parainfluenza virus 1 RNA [Presence] in Respiratory system specimen by NAA with probe detection |
| 55 | http://loinc.org | 92139-5 | Parainfluenza virus 2 RNA [Presence] in Respiratory system specimen by NAA with probe detection |
| 55 | http://loinc.org | 92138-7 | Parainfluenza virus 3 RNA [Presence] in Respiratory system specimen by NAA with probe detection |
| 55 | http://loinc.org | 92130-4 | Rhinovirus RNA [Presence] in Respiratory system specimen by NAA with probe detection |
| 55 | http://loinc.org | 92134-6 | Human metapneumovirus RNA [Presence] in Respiratory system specimen by NAA with probe detection |
| 55 | http://loinc.org | 94040-3 | Adenovirus A+B+C+D+E DNA [Presence] in Respiratory system specimen by NAA with probe detection |
| 54 | http://loinc.org | 2746-6 | pH of Venous blood |
| 54 | http://loinc.org | 2021-4 | Carbon dioxide [Partial pressure] in Venous blood |
| 54 | http://loinc.org | 2705-2 | Oxygen [Partial pressure] in Venous blood |
| 54 | http://loinc.org | 14627-4 | Bicarbonate [Moles/volume] in Venous blood |
| 54 | http://loinc.org | 2027-1 | Carbon dioxide, total [Moles/volume] in Venous blood |
| 53 | http://loinc.org | 75636-1 | Emergency severity index [ESI] |
| 53 | http://loinc.org | 85354-9 | Blood Pressure panel with all children optional |
| 49 | http://loinc.org | 3016-3 | Thyrotropin [Units/volume] in Serum or Plasma |
| 46 | http://loinc.org | 80382-5 | Influenza virus A Ag [Presence] in Upper respiratory specimen by Rapid immunoassay |
| 46 | http://loinc.org | 80383-3 | Influenza virus B Ag [Presence] in Upper respiratory specimen by Rapid immunoassay |
| 40 | http://loinc.org | 24467-3 | CD3+CD4+ (T4 helper) cells [#/volume] in Blood |
| 38 | http://loinc.org | 88020-3 | Functional capacity NYHA |
| 33 | http://loinc.org | 21377-7 | Magnesium [Mass/volume] in Blood |
| 33 | http://loinc.org | 71425-3 | Natriuretic peptide.B prohormone N-Terminal [Mass/volume] in Blood by Immunoassay |
| 33 | http://loinc.org | 88021-1 | Objective assessment of cardiovascular disease NYHA |
| 32 | http://loinc.org | 20447-9 | HIV 1 RNA [#/volume] (viral load) in Serum or Plasma by NAA with probe detection |
| 30 | http://loinc.org | 32693-4 | Lactate [Moles/volume] in Blood |
| 30 | http://loinc.org | 88040-1 | Response to cancer treatment |
| 27 | http://loinc.org | 2106-3 | Choriogonadotropin [Presence] in Urine |
| 17 | http://loinc.org | 75443-2 | Mental health Outpatient Note |
| 17 | http://loinc.org | 84215-3 | Mental health Telehealth Note |
| 13 | http://loinc.org | 88262-1 | Gram positive blood culture panel by Probe in Positive blood culture |
| 13 | http://loinc.org | 44963-7 | Capillary refill [Time] of Nail bed |
| 13 | http://loinc.org | 8478-0 | Mean blood pressure |
| 12 | http://loinc.org | 46288-7 | US Guidance for biopsy of Prostate |
| 12 | http://loinc.org | 21908-9 | Stage group.clinical Cancer |
| 8 | http://loinc.org | 59557-9 | Treatment status Cancer |
| 6 | http://loinc.org | 44667-4 | Site of distant metastasis in Breast tumor |
| 6 | http://loinc.org | 21907-1 | Distant metastases.clinical [Class] Cancer |
| 6 | http://loinc.org | 33728-7 | Size.maximum dimension in Tumor |
| 6 | http://loinc.org | 21905-5 | Primary tumor.clinical [Class] Cancer |
| 6 | http://loinc.org | 21906-3 | Regional lymph nodes.clinical [Class] Cancer |
| 6 | http://loinc.org | 85319-2 | HER2 [Presence] in Breast cancer specimen by Immune stain |
| 6 | http://loinc.org | 85318-4 | ERBB2 gene duplication [Presence] in Breast cancer specimen by FISH |
| 6 | http://loinc.org | 85337-4 | Estrogen receptor Ag [Presence] in Breast cancer specimen by Immune stain |
| 6 | http://loinc.org | 85339-0 | Progesterone receptor Ag [Presence] in Breast cancer specimen by Immune stain |
| 5 | http://loinc.org | 86923-0 | Kansas City Cardiomyopathy Questionnaire - 12 item [KCCQ-12] |
| 5 | http://loinc.org | 86924-8 | Overall summary score [KCCQ-12] |
| 5 | http://loinc.org | 10480-2 | Estrogen+Progesterone receptor Ag [Presence] in Tissue by Immune stain |
| 5 | http://loinc.org | 66519-0 | Percentage area affected by eczema Head and Neck [PhenX] |
| 5 | http://loinc.org | 66529-9 | Percentage area affected by eczema Trunk [PhenX] |
| 5 | http://loinc.org | 66524-0 | Percentage area affected by eczema Upper extremity - bilateral [PhenX] |
| 5 | http://loinc.org | 66534-9 | Percentage area affected by eczema Lower extremity - bilateral [PhenX] |
| 4 | http://loinc.org | 26464-8 | Leukocytes [#/volume] in Blood |
| 4 | http://loinc.org | 26453-1 | Erythrocytes [#/volume] in Blood |
| 4 | http://loinc.org | 30428-7 | MCV [Entitic mean volume] in Red Blood Cells |
| 4 | http://loinc.org | 30385-9 | Erythrocyte [DistWidth] in Blood |
| 4 | http://loinc.org | 26515-7 | Platelets [#/volume] in Blood |
| 4 | http://loinc.org | 42719-5 | Bilirubin.total [Mass/volume] in Blood |
| 4 | http://loinc.org | 33037-3 | Anion gap in Serum or Plasma by calculation |
| 4 | http://loinc.org | 80271-0 | Physical findings of Abdomen by Palpation |
| 3 | http://snomed.info/sct | 271605009 | Position of body and posture (observable entity) |
| 3 | http://snomed.info/sct | 285285000 | Cobb angle (observable entity) |
| 3 | http://snomed.info/sct | 870537001 | Risser sign (finding) |
| 3 | http://loinc.org | 3024-7 | Thyroxine (T4) free [Mass/volume] in Serum or Plasma |
| 3 | http://loinc.org | 70006-2 | Medication management note |
| 2 | http://loinc.org | 85352-3 | Lymph nodes with isolated tumor cells [#] in Cancer specimen by Light microscopy |
| 2 | http://loinc.org | 72091-2 | Knee injury and Osteoarthritis Outcome Score [KOOS] |
| 2 | http://loinc.org | 72098-7 | Quality of life score [KOOS] |
| 2 | http://loinc.org | 72099-5 | Sport-recreation score [KOOS] |
| 2 | http://loinc.org | 72100-1 | Activities of daily living score [KOOS] |
| 2 | http://loinc.org | 72102-7 | Pain score [KOOS] |
| 2 | http://loinc.org | 72101-9 | Symptoms score [KOOS] |
| 2 | http://loinc.org | 85344-0 | Lymph nodes with micrometastases [#] in Cancer specimen by Light microscopy |
| 2 | http://loinc.org | 85343-2 | Lymph nodes with macrometastases [#] in Cancer specimen by Light microscopy |
| 1 | http://loinc.org | 600-7 | Bacteria identified in Blood by Culture |
| 1 | http://loinc.org | 7917-8 | HIV 1 Ab [Presence] in Serum |
| 1 | http://loinc.org | 21924-6 | Tumor marker Cancer |
| 1 | http://loinc.org | 18752-6 | Exercise stress test study |
