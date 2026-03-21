import { Client, isFullPage } from '@notionhq/client';
import type { PageObjectResponse } from '@notionhq/client/build/src/api-endpoints';
import type {
  Vertical,
  Market,
  UseCase,
  Workflow,
  Evidence,
  NodePatch,
} from '../types';

const notion = new Client({ auth: process.env.NOTION_API_KEY });

const DB = {
  verticals: process.env.NOTION_VERTICALS_DB_ID!,
  markets: process.env.NOTION_MARKETS_DB_ID!,
  useCases: process.env.NOTION_USE_CASES_DB_ID!,
  workflows: process.env.NOTION_WORKFLOWS_DB_ID!,
  evidence: process.env.NOTION_EVIDENCE_DB_ID!,
};

// --- Property extractors ---

function textValue(page: PageObjectResponse, name: string): string {
  const p = page.properties[name];
  if (!p) return '';
  if (p.type === 'title') return p.title[0]?.plain_text ?? '';
  if (p.type === 'rich_text') return p.rich_text[0]?.plain_text ?? '';
  return '';
}

function selectValue(page: PageObjectResponse, name: string): string {
  const p = page.properties[name];
  if (!p || p.type !== 'select') return '';
  return p.select?.name ?? '';
}

function numberValue(page: PageObjectResponse, name: string): number | null {
  const p = page.properties[name];
  if (!p || p.type !== 'number') return null;
  return p.number ?? null;
}

function urlValue(page: PageObjectResponse, name: string): string {
  const p = page.properties[name];
  if (!p || p.type !== 'url') return '';
  return p.url ?? '';
}

function dateValue(page: PageObjectResponse, name: string): string {
  const p = page.properties[name];
  if (!p || p.type !== 'date') return '';
  return p.date?.start ?? '';
}

function relationId(page: PageObjectResponse, name: string): string {
  const p = page.properties[name];
  if (!p || p.type !== 'relation') return '';
  return p.relation[0]?.id ?? '';
}

function sharedFields(page: PageObjectResponse) {
  return {
    marketNeed: selectValue(page, 'Market Need') as import('../types').RatingLevel,
    willingnessToPay: selectValue(page, 'Willingness to Pay') as import('../types').RatingLevel,
    technicalFeasibility: selectValue(page, 'Technical Feasibility') as import('../types').RatingLevel,
    regulatoryFeasibility: selectValue(page, 'Regulatory Feasibility') as import('../types').RatingLevel,
    easeOfEntry: selectValue(page, 'Ease of Entry') as import('../types').RatingLevel,
    currentDeployments: textValue(page, 'Current Deployments'),
    alternativeSolutions: textValue(page, 'Alternative Solutions'),
  };
}

// --- Fetch helpers ---

export async function fetchVerticals(): Promise<Vertical[]> {
  const res = await notion.databases.query({
    database_id: DB.verticals,
    sorts: [{ property: 'Priority', direction: 'ascending' }],
  });
  return res.results.filter(isFullPage).map((p) => ({
    id: p.id,
    name: textValue(p, 'Name'),
    description: textValue(p, 'Description'),
    status: (selectValue(p, 'Status') || 'Active') as Vertical['status'],
    priority: numberValue(p, 'Priority') ?? 0,
    owner: selectValue(p, 'Owner'),
    lastEdited: p.last_edited_time,
    ...sharedFields(p),
  }));
}

export async function fetchMarkets(): Promise<Market[]> {
  const res = await notion.databases.query({
    database_id: DB.markets,
    sorts: [{ property: 'Priority', direction: 'ascending' }],
  });
  return res.results.filter(isFullPage).map((p) => ({
    id: p.id,
    name: textValue(p, 'Name'),
    description: textValue(p, 'Description'),
    status: (selectValue(p, 'Status') || 'Exploring') as Market['status'],
    tam: numberValue(p, 'TAM'),
    verticalId: relationId(p, 'Vertical'),
    priority: numberValue(p, 'Priority') ?? 0,
    lastEdited: p.last_edited_time,
    ...sharedFields(p),
  }));
}

export async function fetchUseCases(): Promise<UseCase[]> {
  const res = await notion.databases.query({
    database_id: DB.useCases,
    sorts: [{ property: 'Priority', direction: 'ascending' }],
  });
  return res.results.filter(isFullPage).map((p) => ({
    id: p.id,
    name: textValue(p, 'Name'),
    description: textValue(p, 'Description'),
    status: (selectValue(p, 'Status') || 'Exploring') as UseCase['status'],
    priority: numberValue(p, 'Priority') ?? 0,
    owner: selectValue(p, 'Owner'),
    marketId: relationId(p, 'Market'),
    lastEdited: p.last_edited_time,
    ...sharedFields(p),
  }));
}

export async function fetchWorkflows(): Promise<Workflow[]> {
  const res = await notion.databases.query({ database_id: DB.workflows });
  return res.results.filter(isFullPage).map((p) => ({
    id: p.id,
    name: textValue(p, 'Name'),
    description: textValue(p, 'Description'),
    type: (selectValue(p, 'Type') || 'Desirability') as Workflow['type'],
    confidence: (selectValue(p, 'Confidence') || 'Untested') as Workflow['confidence'],
    score: numberValue(p, 'Score') ?? 50,
    status: (selectValue(p, 'Status') || 'Open') as Workflow['status'],
    owner: selectValue(p, 'Owner'),
    useCaseId: relationId(p, 'Use Case'),
    lastEdited: p.last_edited_time,
    ...sharedFields(p),
  }));
}

export async function fetchEvidence(workflowId: string): Promise<Evidence[]> {
  const res = await notion.databases.query({
    database_id: DB.evidence,
    filter: { property: 'Workflow', relation: { contains: workflowId } },
  });
  return res.results.filter(isFullPage).map((p) => ({
    id: p.id,
    name: textValue(p, 'Name'),
    notes: textValue(p, 'Notes'),
    direction: (selectValue(p, 'Direction') || 'Neutral') as Evidence['direction'],
    strength: (selectValue(p, 'Strength') || 'Anecdotal') as Evidence['strength'],
    source: urlValue(p, 'Source'),
    sourceType: (selectValue(p, 'Source Type') || 'Article') as Evidence['sourceType'],
    dateCollected: dateValue(p, 'Date Collected'),
    collector: selectValue(p, 'Collector'),
    workflowId,
    useCaseId: relationId(p, 'Use Case'),
    marketId: relationId(p, 'Market'),
    verticalId: relationId(p, 'Vertical'),
    ...sharedFields(p),
  }));
}

// --- Write helpers ---

export async function updateNode(
  id: string,
  patch: NodePatch,
  lastEdited: string,
): Promise<{ conflict: boolean }> {
  const page = await notion.pages.retrieve({ page_id: id });
  if (!isFullPage(page)) return { conflict: false };
  if (page.last_edited_time !== lastEdited) return { conflict: true };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const properties: Record<string, any> = {};

  if (patch.name !== undefined)
    properties['Name'] = { title: [{ text: { content: patch.name } }] };
  if (patch.description !== undefined)
    properties['Description'] = { rich_text: [{ text: { content: patch.description } }] };
  if (patch.status !== undefined)
    properties['Status'] = { select: { name: patch.status } };
  if (patch.priority !== undefined)
    properties['Priority'] = { number: patch.priority };
  if (patch.owner !== undefined)
    properties['Owner'] = { select: { name: patch.owner } };
  if (patch.tam !== undefined)
    properties['TAM'] = patch.tam !== null ? { number: patch.tam } : { number: null };
  if (patch.type !== undefined)
    properties['Type'] = { select: { name: patch.type } };
  if (patch.confidence !== undefined)
    properties['Confidence'] = { select: { name: patch.confidence } };
  if (patch.score !== undefined)
    properties['Score'] = { number: patch.score };
  if (patch.marketNeed !== undefined)
    properties['Market Need'] = patch.marketNeed ? { select: { name: patch.marketNeed } } : { select: null };
  if (patch.willingnessToPay !== undefined)
    properties['Willingness to Pay'] = patch.willingnessToPay ? { select: { name: patch.willingnessToPay } } : { select: null };
  if (patch.technicalFeasibility !== undefined)
    properties['Technical Feasibility'] = patch.technicalFeasibility ? { select: { name: patch.technicalFeasibility } } : { select: null };
  if (patch.regulatoryFeasibility !== undefined)
    properties['Regulatory Feasibility'] = patch.regulatoryFeasibility ? { select: { name: patch.regulatoryFeasibility } } : { select: null };
  if (patch.easeOfEntry !== undefined)
    properties['Ease of Entry'] = patch.easeOfEntry ? { select: { name: patch.easeOfEntry } } : { select: null };
  if (patch.currentDeployments !== undefined)
    properties['Current Deployments'] = { rich_text: [{ text: { content: patch.currentDeployments } }] };
  if (patch.alternativeSolutions !== undefined)
    properties['Alternative Solutions'] = { rich_text: [{ text: { content: patch.alternativeSolutions } }] };

  await notion.pages.update({ page_id: id, properties });
  return { conflict: false };
}

export async function createEvidence(
  data: Omit<Evidence, 'id'>,
): Promise<Evidence> {
  const page = await notion.pages.create({
    parent: { database_id: DB.evidence },
    properties: {
      Name: { title: [{ text: { content: data.name } }] },
      Notes: { rich_text: [{ text: { content: data.notes } }] },
      Direction: { select: { name: data.direction } },
      Strength: { select: { name: data.strength } },
      Source: data.source ? { url: data.source } : { url: null },
      'Source Type': { select: { name: data.sourceType } },
      'Date Collected': data.dateCollected
        ? { date: { start: data.dateCollected } }
        : { date: null },
      Collector: { select: { name: data.collector } },
      Workflow: { relation: [{ id: data.workflowId }] },
    },
  });
  return { ...data, id: page.id };
}
