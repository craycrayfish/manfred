export type VerticalStatus = 'Active' | 'Parked' | 'Killed';
export type MarketStatus = 'Exploring' | 'Validated' | 'Invalidated' | 'Parked';
export type UseCaseStatus = 'Exploring' | 'Validated' | 'Invalidated' | 'Parked';
export type WorkflowStatus = 'Open' | 'Testing' | 'Validated' | 'Invalidated';
export type WorkflowType = 'Desirability' | 'Feasibility' | 'Viability';
export type ConfidenceLevel = 'Untested' | 'Low' | 'Medium' | 'High' | 'Validated' | 'Invalidated';
export type EvidenceDirection = 'Supporting' | 'Contradicting' | 'Neutral';
export type EvidenceStrength = 'Anecdotal' | 'Qualitative' | 'Quantitative' | 'Statistical';
export type EvidenceSourceType =
  | 'Interview'
  | 'Survey'
  | 'Article'
  | 'Data'
  | 'Observation'
  | 'Expert Opinion';

// 1–5 rating scale used for all assessment select fields
export type RatingLevel = '1' | '2' | '3' | '4' | '5' | '';

// Assessment fields shared across all four tree levels + Evidence
interface AssessmentFields {
  marketNeed: RatingLevel;
  willingnessToPay: RatingLevel;
  technicalFeasibility: RatingLevel;
  regulatoryFeasibility: RatingLevel;
  easeOfEntry: RatingLevel;   // select 1–5
  currentDeployments: string;     // rich_text
  alternativeSolutions: string;   // rich_text
}

export interface Vertical extends AssessmentFields {
  id: string;
  name: string;
  description: string;
  status: VerticalStatus;
  priority: number;
  owner: string;
  lastEdited: string;
}

export interface Market extends AssessmentFields {
  id: string;
  name: string;
  description: string;
  status: MarketStatus;
  tam: number | null;
  verticalId: string;
  priority: number;
  lastEdited: string;
}

export interface UseCase extends AssessmentFields {
  id: string;
  name: string;
  description: string;
  status: UseCaseStatus;
  priority: number;
  owner: string;
  marketId: string;
  lastEdited: string;
}

export interface Workflow extends AssessmentFields {
  id: string;
  name: string;
  description: string;
  type: WorkflowType;
  confidence: ConfidenceLevel;
  score: number;
  status: WorkflowStatus;
  owner: string;
  useCaseId: string;
  lastEdited: string;
}

export interface Evidence extends AssessmentFields {
  id: string;
  name: string;
  notes: string;
  direction: EvidenceDirection;
  strength: EvidenceStrength;
  source: string;
  sourceType: EvidenceSourceType;
  dateCollected: string;
  collector: string;
  workflowId: string;
  useCaseId: string;
  marketId: string;
  verticalId: string;
}

export interface TreeData {
  verticals: Vertical[];
  markets: Market[];
  useCases: UseCase[];
  workflows: Workflow[];
}

export type AnyNode =
  | (Vertical & { nodeType: 'vertical' })
  | (Market & { nodeType: 'market' })
  | (UseCase & { nodeType: 'useCase' })
  | (Workflow & { nodeType: 'workflow' });

export interface NodePatch {
  name?: string;
  description?: string;
  status?: string;
  priority?: number;
  owner?: string;
  tam?: number | null;
  type?: string;
  confidence?: string;
  score?: number;
  marketNeed?: string;
  willingnessToPay?: string;
  technicalFeasibility?: string;
  regulatoryFeasibility?: string;
  easeOfEntry?: string;
  currentDeployments?: string;
  alternativeSolutions?: string;
}
