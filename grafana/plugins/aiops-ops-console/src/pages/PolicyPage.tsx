/**
 * Policy Viewer Page - Read-only policy configuration
 */

import React, { useState, useEffect } from 'react';
import {
  Button,
  HorizontalGroup,
  VerticalGroup,
  Alert,
  Spinner,
  Card,
  Badge,
  Tab,
  TabsBar,
  TabContent,
} from '@grafana/ui';
import { apiClient } from '../api/client';
import type { Policy, PolicySection } from '../types';
import { formatTimestamp } from '../utils/helpers';

export function PolicyPage() {
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('ingest');
  const [diff, setDiff] = useState<{ diff: string; has_changes: boolean } | null>(null);

  useEffect(() => {
    loadPolicy();
    loadDiff();
  }, []);

  const loadPolicy = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getPolicy();
      setPolicy(response.data || null);
    } catch (err: any) {
      setError(err.message || 'Failed to load policy');
      console.error('Error loading policy:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadDiff = async () => {
    try {
      const response = await apiClient.getPolicyDiff();
      setDiff(response.data || null);
    } catch (err: any) {
      console.error('Error loading policy diff:', err);
    }
  };

  const renderPolicySection = (section: PolicySection | undefined, sectionName: string) => {
    if (!section) {
      return (
        <Alert title={`${sectionName} Configuration`} severity="info">
          No configuration available for this section.
        </Alert>
      );
    }

    return (
      <Card>
        <Card.Heading>{sectionName} Configuration</Card.Heading>
        <Card.Meta>
          <HorizontalGroup spacing="sm">
            <Badge text={section.source} color={section.source === 'default' ? 'blue' : section.source === 'override' ? 'orange' : 'purple'} />
            {section.effective && <Badge text="Effective" color="green" />}
          </HorizontalGroup>
        </Card.Meta>
        <Card.Description>
          <pre style={{ padding: '12px', background: '#f5f5f5', borderRadius: '4px', fontSize: '12px', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {JSON.stringify(section.values, null, 2)}
          </pre>
        </Card.Description>
      </Card>
    );
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (!policy) {
    return (
      <div style={{ padding: '20px' }}>
        <Alert title="No Policy" severity="error">
          Policy configuration could not be loaded.
        </Alert>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <VerticalGroup spacing="lg">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Policy Configuration</h2>
          <Button icon="sync" onClick={loadPolicy} disabled={loading}>
            Refresh
          </Button>
        </div>

        {error && <Alert title="Error" severity="error">{error}</Alert>}

        <Alert title="Read-Only Mode" severity="info">
          Policy configuration is read-only on ship. Changes must be made through the shore-side GitOps workflow.
        </Alert>

        <Card>
          <Card.Heading>Policy Information</Card.Heading>
          <Card.Description>
            <VerticalGroup spacing="sm">
              <div><strong>Schema Version:</strong> {policy.schema_version}</div>
              <div><strong>Last Updated:</strong> {formatTimestamp(policy.last_updated)}</div>
              <div><strong>Source:</strong> {policy.source}</div>
            </VerticalGroup>
          </Card.Description>
        </Card>

        {diff && diff.has_changes && (
          <Alert title="Policy Diff Available" severity="warning">
            <div style={{ marginBottom: '8px' }}>
              This ship's policy differs from the fleet default. Review the differences below.
            </div>
            <details>
              <summary>View Diff</summary>
              <pre style={{ marginTop: '8px', padding: '8px', background: '#fff', borderRadius: '4px', fontSize: '11px', overflow: 'auto' }}>
                {diff.diff}
              </pre>
            </details>
          </Alert>
        )}

        <TabsBar>
          <Tab label="Ingest" active={activeTab === 'ingest'} onChangeTab={() => setActiveTab('ingest')} />
          <Tab label="Detect" active={activeTab === 'detect'} onChangeTab={() => setActiveTab('detect')} />
          <Tab label="Correlate" active={activeTab === 'correlate'} onChangeTab={() => setActiveTab('correlate')} />
          <Tab label="Notify" active={activeTab === 'notify'} onChangeTab={() => setActiveTab('notify')} />
          <Tab label="Remediate" active={activeTab === 'remediate'} onChangeTab={() => setActiveTab('remediate')} />
          <Tab label="LLM" active={activeTab === 'llm'} onChangeTab={() => setActiveTab('llm')} />
          <Tab label="Retention" active={activeTab === 'retention'} onChangeTab={() => setActiveTab('retention')} />
          <Tab label="Privacy" active={activeTab === 'privacy'} onChangeTab={() => setActiveTab('privacy')} />
          <Tab label="SLO" active={activeTab === 'slo'} onChangeTab={() => setActiveTab('slo')} />
        </TabsBar>

        <TabContent>
          {activeTab === 'ingest' && renderPolicySection(policy.sections.ingest, 'Ingest')}
          {activeTab === 'detect' && renderPolicySection(policy.sections.detect, 'Detect')}
          {activeTab === 'correlate' && renderPolicySection(policy.sections.correlate, 'Correlate')}
          {activeTab === 'notify' && renderPolicySection(policy.sections.notify, 'Notify')}
          {activeTab === 'remediate' && renderPolicySection(policy.sections.remediate, 'Remediate')}
          {activeTab === 'llm' && renderPolicySection(policy.sections.llm, 'LLM')}
          {activeTab === 'retention' && renderPolicySection(policy.sections.retention, 'Retention')}
          {activeTab === 'privacy' && renderPolicySection(policy.sections.privacy, 'Privacy')}
          {activeTab === 'slo' && renderPolicySection(policy.sections.slo, 'SLO')}
        </TabContent>

        <Alert title="Policy Management" severity="info">
          <p><strong>Effective Policy:</strong> The currently active policy on this ship.</p>
          <p><strong>Source Indicators:</strong></p>
          <ul style={{ marginLeft: '20px', marginTop: '8px' }}>
            <li><Badge text="default" color="blue" /> - Using fleet default values</li>
            <li><Badge text="override" color="orange" /> - Ship-specific override applied</li>
            <li><Badge text="fleet" color="purple" /> - Fleet-wide policy from shore</li>
          </ul>
          <p style={{ marginTop: '8px' }}>
            To propose policy changes, contact the shore operations team with your GitOps workflow.
          </p>
        </Alert>
      </VerticalGroup>
    </div>
  );
}
