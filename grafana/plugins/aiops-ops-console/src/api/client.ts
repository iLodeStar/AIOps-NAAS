/**
 * API Client for AIOps Operations Console
 * All calls go through Grafana's data source proxy to avoid CORS
 */

import { getBackendSrv } from '@grafana/runtime';
import type {
  Incident,
  IncidentFilter,
  Approval,
  Action,
  ActionExecution,
  Policy,
  APIResponse,
  PaginatedResponse,
} from '../types';

const API_BASE = '/api/datasources/proxy/uid/aiops-incident-api';

export class AIOpsAPIClient {
  /**
   * Incidents API
   */
  async getIncidents(filters?: IncidentFilter): Promise<PaginatedResponse<Incident>> {
    const params = new URLSearchParams();
    if (filters?.severity) params.append('severity', filters.severity.join(','));
    if (filters?.type) params.append('type', filters.type.join(','));
    if (filters?.status) params.append('status', filters.status.join(','));
    if (filters?.ship_id) params.append('ship_id', filters.ship_id);
    if (filters?.search) params.append('search', filters.search);
    if (filters?.page) params.append('page', filters.page.toString());
    if (filters?.per_page) params.append('per_page', filters.per_page.toString());

    return getBackendSrv().get(`${API_BASE}/api/incidents?${params}`);
  }

  async getIncident(incidentId: string): Promise<APIResponse<Incident>> {
    return getBackendSrv().get(`${API_BASE}/api/incidents/${incidentId}`);
  }

  async updateIncidentStatus(
    incidentId: string,
    status: string,
    explanation?: string
  ): Promise<APIResponse<Incident>> {
    return getBackendSrv().patch(`${API_BASE}/api/incidents/${incidentId}`, {
      status,
      explanation,
    });
  }

  async acknowledgeIncident(incidentId: string, comment?: string): Promise<APIResponse<Incident>> {
    return getBackendSrv().patch(`${API_BASE}/api/incidents/${incidentId}`, {
      status: 'ack',
      explanation: comment || 'Acknowledged',
    });
  }

  async resolveIncident(incidentId: string, resolution?: string): Promise<APIResponse<Incident>> {
    return getBackendSrv().patch(`${API_BASE}/api/incidents/${incidentId}`, {
      status: 'resolved',
      explanation: resolution || 'Resolved',
    });
  }

  async suppressIncident(incidentId: string, reason?: string): Promise<APIResponse<Incident>> {
    return getBackendSrv().patch(`${API_BASE}/api/incidents/${incidentId}`, {
      status: 'suppressed',
      explanation: reason || 'Suppressed',
    });
  }

  /**
   * Approvals API
   */
  async getPendingApprovals(): Promise<APIResponse<Approval[]>> {
    return getBackendSrv().get(`${API_BASE}/api/approvals/pending`);
  }

  async getMyApprovals(): Promise<APIResponse<Approval[]>> {
    return getBackendSrv().get(`${API_BASE}/api/approvals/mine`);
  }

  async approveAction(
    incidentId: string,
    approvalId: string,
    comment?: string
  ): Promise<APIResponse<Approval>> {
    return getBackendSrv().post(`${API_BASE}/api/incidents/${incidentId}/approve`, {
      approval_id: approvalId,
      action: 'approve',
      comment: comment || '',
    });
  }

  async rejectAction(
    incidentId: string,
    approvalId: string,
    reason: string
  ): Promise<APIResponse<Approval>> {
    return getBackendSrv().post(`${API_BASE}/api/incidents/${incidentId}/approve`, {
      approval_id: approvalId,
      action: 'reject',
      comment: reason,
    });
  }

  /**
   * Actions API
   */
  async getAvailableActions(): Promise<APIResponse<Action[]>> {
    return getBackendSrv().get(`${API_BASE}/api/actions`);
  }

  async executeAction(
    actionId: string,
    incidentId: string,
    parameters: Record<string, any>
  ): Promise<APIResponse<ActionExecution>> {
    return getBackendSrv().post(`${API_BASE}/api/actions/execute`, {
      action_id: actionId,
      incident_id: incidentId,
      params: parameters,
    });
  }

  async getActionExecution(executionId: string): Promise<APIResponse<ActionExecution>> {
    return getBackendSrv().get(`${API_BASE}/api/actions/executions/${executionId}`);
  }

  /**
   * Policy API
   */
  async getPolicy(): Promise<APIResponse<Policy>> {
    return getBackendSrv().get(`${API_BASE}/api/policy`);
  }

  async getPolicyDiff(): Promise<APIResponse<{ diff: string; has_changes: boolean }>> {
    return getBackendSrv().get(`${API_BASE}/api/policy/diff`);
  }

  /**
   * Audit API
   */
  async logAuditEvent(event: {
    action: string;
    resource: string;
    details: Record<string, any>;
  }): Promise<APIResponse<void>> {
    return getBackendSrv().post(`${API_BASE}/api/audit`, event);
  }
}

// Singleton instance
export const apiClient = new AIOpsAPIClient();
