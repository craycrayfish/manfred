# Notion Database Registry

This file lists known Notion databases so that skills (deep-research, entity-search) can automatically select the right database for a research task without asking the user.

**How to use this file:**
- Before starting research, scan the entries below for a database that matches the topic.
- If a match exists, use its Database ID / Data Source ID and schema to guide what fields to research and where to save.
- If no match exists, fall back to the normal interactive flow (ask the user).
- After creating a new database, add an entry here following the format below.

---

## Facility Directory
- **Database ID**: `e6c3c6a3a5494c6ca58f92bc4123b33a`
- **Data Source ID**: `7a311746-431d-440d-b6aa-bc68ffeeff33`
- **URL**: https://www.notion.so/e6c3c6a3a5494c6ca58f92bc4123b33a
- **Parent Page**: Elderly Care Facilities
- **Purpose**: Directory of elderly care facilities with contact info, location, type, and research/outreach status
- **Schema**:
  | Property | Type | Description |
  |----------|------|-------------|
  | Name | title | Facility name |
  | Address | text | Street address |
  | City | select | City name |
  | State | select | US state abbreviation (e.g. CA, TX, OR) |
  | Phone | text | Main phone number |
  | Facility Type | multi_select | Assisted Living, Memory Care, Skilled Nursing, CCRC, Board and Care, Independent Living, Community Based, Daycare, Home Care |
  | Website | url | Facility website |
  | Beds | number | Number of beds |
  | Owner Type | select | Family, PE |
  | Parent Company | multi_select | Parent/management company name |
  | Status | status | Not started, Outreach done, Visit Scheduled, Visit Completed, Done |
  | Research Status | status | Not started, In progress, Done |
  | Assignee | person | Team member assigned |
  | Administrator Name | text | Facility administrator name |
  | Administrator Phone | phone_number | Administrator phone |
  | Administrator Email | email | Administrator email |
  | Director of Nursing Name | text | DON name |
  | Director of Nursing Phone | phone_number | DON phone |
  | Director of Nursing (Email) | email | DON email |
  | Notes | text | Additional notes |
- **Notes**: Always include Source URL or Website when adding new facilities. Use existing select/multi-select option values when possible.

---

## People
- **Database ID**: `2f644b67c7b980b4ae7ef6afaa48b82a`
- **Data Source ID**: `collection://2f644b67-c7b9-80ba-a714-000b05f1be6a`
- **URL**: https://www.notion.so/2f644b67c7b980b4ae7ef6afaa48b82a
- **Purpose**: Directory of people relevant to Manfred — advisors, investors, network contacts, potential hires, vendors, etc.
- **Schema**:
  | Property | Type | Description |
  |----------|------|-------------|
  | Name | title | Full name |
  | Title | text | Job title or role |
  | Company | text | Current company or organization |
  | Affiliation | multi_select | e.g. Stanford |
  | Type | multi_select | Advisor, Vendor, Investor, Advice, Hire, Network |
  | Stage | select | Relationship stage |
  | Status | status | Not started, In progress, Done |
  | email | email | Email address |
  | Profile | url | LinkedIn or profile URL |
  | Location | text | City/region |
  | Notes | text | Brief notes |
  | SGD1 | checkbox | SGD1 flag |
- **Notes**: Auto-lookup — search this database whenever the user asks about a person. Add new entries if person is not found. Append research findings to existing person pages.

---

## AI Models
- **Database ID**: `2ea44b67c7b9802c8170f71f98d48492`
- **Data Source ID**: `2ea44b67-c7b9-8020-8673-000be59800ff`
- **URL**: https://www.notion.so/2ea44b67c7b9802c8170f71f98d48492
- **Parent Page**: Tech Research
- **Purpose**: Catalog of AI models (robotics, TTS, etc.) with technical details (architecture, parameters, training data, approach)
- **Schema**:
  | Property | Type | Description |
  |----------|------|-------------|
  | Name | title | Model name |
  | Maker | select | Company/lab that created the model (e.g. 1x, NVIDIA, Alibaba / Qwen) |
  | Model Type | select | Model category (e.g. VLA, TTS) |
  | Parameters | text | Model parameter count or size |
  | Approach | text | Training/learning approach |
  | Data Used | text | Training data description |
  | Architecture | text | Model architecture details |
  | Size (GB) | number | Model size in GB |
  | Source | url | Paper or announcement URL |
- **Notes**: Always include Source URL. New select options for Maker/Model Type must be added manually in Notion UI before they can be set via API.

---

## Research Articles
- **Database ID**: `31b44b67c7b980eea38cfe29736ad5d8`
- **Data Source ID**: `31b44b67-c7b9-801e-8220-000b5a77f12b`
- **URL**: https://www.notion.so/31b44b67c7b980eea38cfe29736ad5d8
- **Purpose**: Catalog of research papers and news articles relevant to Manfred/Qrobots, linked to People (authors)
- **Schema**:
  | Property | Type | Description |
  |----------|------|-------------|
  | Title | title | Article/paper title |
  | Authors | relation | Relation to People database (authors) |
  | Source | url | URL to the article/paper |
  | Type | select | Paper, News |
  | Summary | rich_text | 2-3 sentence summary of key topic and conclusions |
- **Notes**: Authors relation links to the People database. Type options: "Paper", "News".

---

## Hypothesis Tree — Assessment fields (shared across all 5 tables)
All five hypothesis tree tables share these assessment columns:
| Property | Type | Options | Description |
|----------|------|---------|-------------|
| Market Need | select | 1, 2, 3, 4, 5 | Strength of market need rating |
| Willingness to Pay | select | 1, 2, 3, 4, 5 | Customer WTP rating |
| Technical Feasibility | select | 1, 2, 3, 4, 5 | Technical difficulty rating |
| Regulatory Feasibility | select | 1, 2, 3, 4, 5 | Regulatory risk rating |
| Ease of Entry | select | 1, 2, 3, 4, 5 | Ease of market entry rating |
| Current Deployments | rich_text | — | Notes on existing market solutions |
| Alternative Solutions | rich_text | — | Notes on alternative approaches |

---

## Hypothesis Tree — Verticals
- **Database ID**: `c77239d3557e414f82faa23149f461e5`
- **Data Source ID**: `818fb1d6-7477-4e0d-ad94-5ba7fb4e6177`
- **URL**: https://www.notion.so/c77239d3557e414f82faa23149f461e5
- **Parent Page**: Hypothesis Tree
- **Purpose**: Top-level startup verticals being explored (e.g., "Skilled Nursing Facilities")
- **Schema**:
  | Property | Type | Options |
  |----------|------|---------|
  | Name | title | — |
  | Description | rich_text | — |
  | Status | select | Active, Parked, Killed |
  | Priority | number | — |
  | Owner | select | Shawn, Co-founder, Agent |
  | + all shared assessment fields | | |
- **Notes**: Root of the hypothesis tree. Created by /seed-tree skill.

---

## Hypothesis Tree — Markets
- **Database ID**: `cdc8f63549ee47f6bbcb8fa4be0daa3b`
- **Data Source ID**: `2d632b83-abc8-4ffb-aab6-77337c7c6e15`
- **URL**: https://www.notion.so/cdc8f63549ee47f6bbcb8fa4be0daa3b
- **Parent Page**: Hypothesis Tree
- **Purpose**: Market segments within each vertical (e.g., "Call Light Response in SNFs")
- **Schema**:
  | Property | Type | Options |
  |----------|------|---------|
  | Name | title | — |
  | Description | rich_text | — |
  | Status | select | Exploring, Validated, Invalidated, Parked |
  | TAM | number | $M |
  | Priority | number | — |
  | Vertical | relation | → Verticals |
  | + all shared assessment fields | | |
- **Notes**: Second level of the hypothesis tree. MECE within each vertical.

---

## Hypothesis Tree — Use Cases
- **Database ID**: `5406b28931eb44748944aea1daa840a9`
- **Data Source ID**: `209d7467-f826-4541-a0b5-be21e40b3b14`
- **URL**: https://www.notion.so/5406b28931eb44748944aea1daa840a9
- **Parent Page**: Hypothesis Tree
- **Purpose**: Specific job-to-be-done scenarios within each market (e.g., "Resident requests nighttime assistance")
- **Schema**:
  | Property | Type | Options |
  |----------|------|---------|
  | Name | title | — |
  | Description | rich_text | — |
  | Status | select | Exploring, Validated, Invalidated, Parked |
  | Priority | number | — |
  | Owner | select | Shawn, Co-founder, Agent |
  | Market | relation | → Markets |
  | + all shared assessment fields | | |
- **Notes**: Third level of the tree. MECE within each market.

---

## Hypothesis Tree — Workflows
- **Database ID**: `206adcaa981b47089bd08e912eb97b6c`
- **Data Source ID**: `ce94f261-f97e-48a2-ab40-4b8b78b171c3`
- **URL**: https://www.notion.so/206adcaa981b47089bd08e912eb97b6c
- **Parent Page**: Hypothesis Tree
- **Purpose**: Concrete process flows being tested within each use case (desirability, feasibility, viability)
- **Schema**:
  | Property | Type | Options |
  |----------|------|---------|
  | Name | title | — |
  | Description | rich_text | — |
  | Type | select | Desirability, Feasibility, Viability |
  | Confidence | select | Untested, Low, Medium, High, Validated, Invalidated |
  | Score | number | 0–100 composite evidence score |
  | Status | select | Open, Testing, Validated, Invalidated |
  | Owner | select | Shawn, Co-founder, Agent |
  | Use Case | relation | → Use Cases |
  | + all shared assessment fields | | |
- **Notes**: Fourth/leaf level of the tree. Use /research-hypothesis to find evidence and /score-hypothesis to recalculate scores.

---

## Hypothesis Tree — Evidence
- **Database ID**: `559d7d415de54fd2848584b7f562f0cf`
- **Data Source ID**: `22aca84e-0c9b-4598-9dbd-c9e5ad4cb16c`
- **URL**: https://www.notion.so/559d7d415de54fd2848584b7f562f0cf
- **Parent Page**: Hypothesis Tree
- **Purpose**: Individual pieces of evidence (interviews, articles, data) linked to workflows
- **Schema**:
  | Property | Type | Options |
  |----------|------|---------|
  | Name | title | — |
  | Notes | rich_text | — |
  | Direction | select | Supporting, Contradicting, Neutral |
  | Strength | select | Anecdotal, Qualitative, Quantitative, Statistical |
  | Source | url | — |
  | Source Type | select | Interview, Survey, Article, Data, Observation, Expert Opinion |
  | Date Collected | date | — |
  | Collector | select | Shawn, Co-founder, Agent |
  | Workflow | relation | → Workflows |
  | Use Case | relation | → Use Cases |
  | Market | relation | → Markets |
  | Vertical | relation | → Verticals |
  | + all shared assessment fields | | |
- **Notes**: Not shown as a tree level — visible only in the workflow detail panel. Use /log-evidence to add entries.
