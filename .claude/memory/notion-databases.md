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
