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

## Robotics Foundation Models
- **Database ID**: `2ea44b67c7b9802c8170f71f98d48492`
- **Data Source ID**: `2ea44b67-c7b9-8020-8673-000be59800ff`
- **URL**: https://www.notion.so/2ea44b67c7b9802c8170f71f98d48492
- **Parent Page**: Tech Research
- **Purpose**: Catalog of robotics foundation models with technical details (architecture, parameters, training data, approach)
- **Schema**:
  | Property | Type | Description |
  |----------|------|-------------|
  | Name | title | Model name |
  | Maker | select | Company/lab that created the model (e.g. 1x) |
  | Parameters | text | Model parameter count or size |
  | Approach | text | Training/learning approach (e.g. imitation learning, RL) |
  | Data Used | text | Training data description |
  | Architecture | text | Model architecture details |
  | Source | url | Paper or announcement URL |
- **Notes**: Always include Source URL. Add new Maker options as needed for new companies.
