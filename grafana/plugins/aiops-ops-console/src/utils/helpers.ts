/**
 * Utility helper functions for the Ops Console
 */

import type { UserRole, OperatorRole } from '../types';

/**
 * Map Grafana roles to Operator roles
 */
export function mapGrafanaRoleToOperatorRole(grafanaRole: UserRole): OperatorRole {
  switch (grafanaRole) {
    case 'Viewer':
      return 'Operator'; // Read-only
    case 'Editor':
      return 'Engineer'; // Can approve and execute safe actions
    case 'Admin':
      return 'Admin'; // Full access
    default:
      return 'Operator';
  }
}

/**
 * Check if user has permission for an action
 */
export function hasPermission(userRole: UserRole, requiredRole: OperatorRole): boolean {
  const roleHierarchy: Record<OperatorRole, number> = {
    Operator: 1,
    Engineer: 2,
    Admin: 3,
  };

  const userOperatorRole = mapGrafanaRoleToOperatorRole(userRole);
  return roleHierarchy[userOperatorRole] >= roleHierarchy[requiredRole];
}

/**
 * Format timestamp to readable format
 */
export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  return `${diffDay}d ago`;
}

/**
 * Get severity badge color
 */
export function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'red';
    case 'high':
      return 'orange';
    case 'medium':
      return 'yellow';
    case 'low':
      return 'blue';
    default:
      return 'gray';
  }
}

/**
 * Get status badge color
 */
export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'open':
      return 'red';
    case 'ack':
    case 'acknowledged':
      return 'yellow';
    case 'resolved':
      return 'green';
    case 'suppressed':
      return 'gray';
    default:
      return 'gray';
  }
}

/**
 * Get risk level color
 */
export function getRiskColor(risk: string): string {
  switch (risk.toLowerCase()) {
    case 'high':
      return 'red';
    case 'medium':
      return 'orange';
    case 'low':
      return 'green';
    default:
      return 'gray';
  }
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

/**
 * Parse ClickHouse reference URL
 */
export function parseClickHouseRef(ref: string): { table: string; query: string } | null {
  const match = ref.match(/clickhouse:\/\/([^/]+)\/(.*)/);
  if (!match) return null;
  return { table: match[1], query: match[2] };
}

/**
 * Check if action is on cooldown
 */
export function isOnCooldown(lastExecuted: string | undefined, cooldownSec: number): boolean {
  if (!lastExecuted) return false;
  const lastExecDate = new Date(lastExecuted);
  const now = new Date();
  const diffMs = now.getTime() - lastExecDate.getTime();
  const diffSec = diffMs / 1000;
  return diffSec < cooldownSec;
}

/**
 * Calculate time until cooldown ends
 */
export function timeUntilAvailable(lastExecuted: string, cooldownSec: number): string {
  const lastExecDate = new Date(lastExecuted);
  const availableAt = new Date(lastExecDate.getTime() + cooldownSec * 1000);
  const now = new Date();
  const diffMs = availableAt.getTime() - now.getTime();
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec <= 0) return 'Available now';

  const minutes = Math.floor(diffSec / 60);
  const seconds = diffSec % 60;

  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

/**
 * Validate incident type
 */
export function isValidIncidentType(type: string): boolean {
  const validTypes = [
    'link_degradation',
    'resource_pressure',
    'auth_failure',
    'comms_outage',
    'app_degradation',
    'network_issue',
    'security_alert',
  ];
  return validTypes.includes(type);
}
