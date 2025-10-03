/**
 * AIOps Operations Console - Type Definitions
 * Based on Version 3 Architecture Data Contracts
 */

export interface TimelineEntry {
  ts: string; // ISO timestamp
  event: string;
  description?: string;
  source?: string;
  metadata?: Record<string, any>;
}

export interface Evidence {
  ref: string; // e.g., "clickhouse://logs.raw/..."
  summary?: string;
  weight?: number;
}

export interface RunbookRef {
  id: string;
  title: string;
  risk?: 'low' | 'medium' | 'high';
}

export interface Incident {
  schema_version: string;
  incident_id: string;
  created_at: string;
  updated_at?: string;
  ship_id: string;
  scope: Array<{
    device_id: string;
    service: string;
  }>;
  type: string; // link_degradation, resource_pressure, auth_failure, etc.
  severity: 'low' | 'medium' | 'high' | 'critical';
  corr_keys: string[];
  suppress_key: string;
  timeline: TimelineEntry[];
  evidence: Evidence[];
  runbook_refs: RunbookRef[];
  status: 'open' | 'ack' | 'resolved' | 'suppressed';
  narrative?: string; // From LLM enrichment
  confidence?: 'low' | 'medium' | 'high';
  owner?: string;
}

export interface IncidentFilter {
  severity?: string[];
  type?: string[];
  status?: string[];
  ship_id?: string;
  search?: string;
  page?: number;
  per_page?: number;
}

export interface Approval {
  approval_id: string;
  incident_id: string;
  incident_type: string;
  incident_severity: string;
  ship_id: string;
  requested_by: string;
  requested_at: string;
  action_type: string;
  action_details: Record<string, any>;
  status: 'pending' | 'approved' | 'rejected';
  approver?: string;
  approved_at?: string;
  comment?: string;
  requires_two_person: boolean;
  approvals_count: number;
  approvals_required: number;
}

export interface Action {
  action_id: string;
  name: string;
  description: string;
  risk: 'low' | 'medium' | 'high';
  allowed: boolean;
  requires_approval: boolean;
  requires_two_person: boolean;
  cooldown_sec: number;
  last_executed?: string;
  next_available?: string;
  parameters?: Array<{
    name: string;
    type: string;
    required: boolean;
    default?: any;
  }>;
}

export interface ActionExecution {
  execution_id: string;
  action_id: string;
  incident_id?: string;
  executed_by: string;
  executed_at: string;
  parameters: Record<string, any>;
  status: 'running' | 'success' | 'failed';
  result?: {
    pre_checks: Record<string, boolean>;
    post_checks: Record<string, boolean>;
    output: string;
    error?: string;
  };
}

export interface PolicySection {
  name: string;
  values: Record<string, any>;
  source: 'default' | 'override' | 'fleet';
  effective: boolean;
}

export interface Policy {
  schema_version: string;
  last_updated: string;
  source: string;
  sections: {
    ingest?: PolicySection;
    detect?: PolicySection;
    correlate?: PolicySection;
    notify?: PolicySection;
    remediate?: PolicySection;
    llm?: PolicySection;
    retention?: PolicySection;
    privacy?: PolicySection;
    slo?: PolicySection;
  };
}

export interface APIResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export type UserRole = 'Viewer' | 'Editor' | 'Admin';
export type OperatorRole = 'Operator' | 'Engineer' | 'Admin';
