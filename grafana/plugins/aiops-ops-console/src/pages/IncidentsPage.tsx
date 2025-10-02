/**
 * Incidents List Page
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Input,
  Select,
  Field,
  HorizontalGroup,
  VerticalGroup,
  Badge,
  Table,
  Column,
  Alert,
  Spinner,
  Pagination,
} from '@grafana/ui';
import { apiClient } from '../api/client';
import type { Incident, IncidentFilter } from '../types';
import { formatRelativeTime, getSeverityColor, getStatusColor } from '../utils/helpers';

export function IncidentsPage() {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<IncidentFilter>({
    page: 1,
    per_page: 20,
  });
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');

  const severityOptions = [
    { label: 'All Severities', value: '' },
    { label: 'Critical', value: 'critical' },
    { label: 'High', value: 'high' },
    { label: 'Medium', value: 'medium' },
    { label: 'Low', value: 'low' },
  ];

  const statusOptions = [
    { label: 'All Statuses', value: '' },
    { label: 'Open', value: 'open' },
    { label: 'Acknowledged', value: 'ack' },
    { label: 'Resolved', value: 'resolved' },
    { label: 'Suppressed', value: 'suppressed' },
  ];

  useEffect(() => {
    loadIncidents();
  }, [filters]);

  const loadIncidents = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getIncidents(filters);
      setIncidents(response.data || []);
      setTotalPages(response.pages || 1);
    } catch (err: any) {
      setError(err.message || 'Failed to load incidents');
      console.error('Error loading incidents:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setFilters({ ...filters, search: searchQuery, page: 1 });
  };

  const handleSeverityChange = (value: string) => {
    setFilters({
      ...filters,
      severity: value ? [value] : undefined,
      page: 1,
    });
  };

  const handleStatusChange = (value: string) => {
    setFilters({
      ...filters,
      status: value ? [value] : undefined,
      page: 1,
    });
  };

  const handleRowClick = (incident: Incident) => {
    navigate(`/incidents/${incident.incident_id}`);
  };

  const columns: Array<Column<Incident>> = [
    {
      id: 'created_at',
      header: 'Time',
      cell: (props) => formatRelativeTime(props.row.original.created_at),
    },
    {
      id: 'severity',
      header: 'Severity',
      cell: (props) => (
        <Badge
          text={props.row.original.severity}
          color={getSeverityColor(props.row.original.severity)}
        />
      ),
    },
    {
      id: 'type',
      header: 'Type',
      cell: (props) => props.row.original.type.replace(/_/g, ' '),
    },
    {
      id: 'scope',
      header: 'Device/Service',
      cell: (props) => {
        const scope = props.row.original.scope[0];
        return scope ? `${scope.device_id} / ${scope.service}` : 'N/A';
      },
    },
    {
      id: 'ship_id',
      header: 'Ship',
      cell: (props) => props.row.original.ship_id,
    },
    {
      id: 'status',
      header: 'Status',
      cell: (props) => (
        <Badge
          text={props.row.original.status}
          color={getStatusColor(props.row.original.status)}
        />
      ),
    },
    {
      id: 'owner',
      header: 'Owner',
      cell: (props) => props.row.original.owner || '-',
    },
  ];

  return (
    <div style={{ padding: '20px' }}>
      <VerticalGroup spacing="lg">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Incidents</h2>
          <Button icon="sync" onClick={loadIncidents} disabled={loading}>
            Refresh
          </Button>
        </div>

        {error && <Alert title="Error" severity="error">{error}</Alert>}

        <HorizontalGroup spacing="md">
          <Field label="Search">
            <Input
              placeholder="Search incidents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.currentTarget.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') handleSearch();
              }}
              suffix={<Button icon="search" variant="secondary" onClick={handleSearch} />}
              width={40}
            />
          </Field>

          <Field label="Severity">
            <Select
              options={severityOptions}
              value={filters.severity?.[0] || ''}
              onChange={(v) => handleSeverityChange(v.value || '')}
              width={20}
            />
          </Field>

          <Field label="Status">
            <Select
              options={statusOptions}
              value={filters.status?.[0] || ''}
              onChange={(v) => handleStatusChange(v.value || '')}
              width={20}
            />
          </Field>
        </HorizontalGroup>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
            <Spinner size="lg" />
          </div>
        ) : (
          <>
            <Table
              data={incidents}
              columns={columns}
              onRowClick={handleRowClick}
              height={600}
            />

            {totalPages > 1 && (
              <Pagination
                currentPage={filters.page || 1}
                numberOfPages={totalPages}
                onNavigate={(page) => setFilters({ ...filters, page })}
              />
            )}
          </>
        )}
      </VerticalGroup>
    </div>
  );
}
