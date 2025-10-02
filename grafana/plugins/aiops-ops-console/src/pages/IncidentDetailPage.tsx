/**
 * Incident Detail Page
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Button,
  HorizontalGroup,
  VerticalGroup,
  Alert,
  Spinner,
  Badge,
  Tab,
  TabsBar,
  TabContent,
  ConfirmModal,
  TextArea,
  Field,
  Card,
} from '@grafana/ui';
import { apiClient } from '../api/client';
import type { Incident } from '../types';
import { formatTimestamp, getSeverityColor, getStatusColor } from '../utils/helpers';

export function IncidentDetailPage() {
  const { incidentId } = useParams<{ incidentId: string }>();
  const navigate = useNavigate();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('summary');
  const [showAckModal, setShowAckModal] = useState(false);
  const [showResolveModal, setShowResolveModal] = useState(false);
  const [showSuppressModal, setShowSuppressModal] = useState(false);
  const [comment, setComment] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (incidentId) {
      loadIncident();
    }
  }, [incidentId]);

  const loadIncident = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getIncident(incidentId!);
      setIncident(response.data || null);
    } catch (err: any) {
      setError(err.message || 'Failed to load incident');
      console.error('Error loading incident:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async () => {
    try {
      setActionLoading(true);
      await apiClient.acknowledgeIncident(incidentId!, comment);
      setShowAckModal(false);
      setComment('');
      await loadIncident();
    } catch (err: any) {
      setError(err.message || 'Failed to acknowledge incident');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResolve = async () => {
    try {
      setActionLoading(true);
      await apiClient.resolveIncident(incidentId!, comment);
      setShowResolveModal(false);
      setComment('');
      await loadIncident();
    } catch (err: any) {
      setError(err.message || 'Failed to resolve incident');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSuppress = async () => {
    try {
      setActionLoading(true);
      await apiClient.suppressIncident(incidentId!, comment);
      setShowSuppressModal(false);
      setComment('');
      await loadIncident();
    } catch (err: any) {
      setError(err.message || 'Failed to suppress incident');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (!incident) {
    return (
      <div style={{ padding: '20px' }}>
        <Alert title="Not Found" severity="error">
          Incident not found
        </Alert>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <VerticalGroup spacing="lg">
        <HorizontalGroup justify="space-between">
          <Button icon="arrow-left" variant="secondary" onClick={() => navigate('/incidents')}>
            Back to Incidents
          </Button>
          <HorizontalGroup>
            {incident.status === 'open' && (
              <Button onClick={() => setShowAckModal(true)}>Acknowledge</Button>
            )}
            {(incident.status === 'open' || incident.status === 'ack') && (
              <Button onClick={() => setShowResolveModal(true)}>Resolve</Button>
            )}
            {incident.status !== 'suppressed' && (
              <Button variant="destructive" onClick={() => setShowSuppressModal(true)}>
                Suppress
              </Button>
            )}
          </HorizontalGroup>
        </HorizontalGroup>

        {error && <Alert title="Error" severity="error">{error}</Alert>}

        <Card>
          <Card.Heading>Incident Details</Card.Heading>
          <Card.Meta>
            <HorizontalGroup spacing="md">
              <Badge text={incident.severity} color={getSeverityColor(incident.severity)} />
              <Badge text={incident.status} color={getStatusColor(incident.status)} />
              <span>{formatTimestamp(incident.created_at)}</span>
            </HorizontalGroup>
          </Card.Meta>
          <Card.Description>
            <VerticalGroup spacing="sm">
              <div><strong>ID:</strong> {incident.incident_id}</div>
              <div><strong>Type:</strong> {incident.type.replace(/_/g, ' ')}</div>
              <div><strong>Ship:</strong> {incident.ship_id}</div>
              <div><strong>Device/Service:</strong> {incident.scope.map(s => `${s.device_id}/${s.service}`).join(', ')}</div>
              {incident.owner && <div><strong>Owner:</strong> {incident.owner}</div>}
            </VerticalGroup>
          </Card.Description>
        </Card>

        <TabsBar>
          <Tab label="Summary" active={activeTab === 'summary'} onChangeTab={() => setActiveTab('summary')} />
          <Tab label="Timeline" active={activeTab === 'timeline'} onChangeTab={() => setActiveTab('timeline')} />
          <Tab label="Evidence" active={activeTab === 'evidence'} onChangeTab={() => setActiveTab('evidence')} />
          <Tab label="Narrative" active={activeTab === 'narrative'} onChangeTab={() => setActiveTab('narrative')} />
          <Tab label="Runbooks" active={activeTab === 'runbooks'} onChangeTab={() => setActiveTab('runbooks')} />
        </TabsBar>

        <TabContent>
          {activeTab === 'summary' && (
            <Card>
              <Card.Heading>Summary</Card.Heading>
              <VerticalGroup spacing="md">
                <div><strong>Correlation Keys:</strong> {incident.corr_keys.join(', ')}</div>
                <div><strong>Suppress Key:</strong> {incident.suppress_key}</div>
                {incident.narrative && (
                  <div>
                    <strong>AI Narrative:</strong>
                    <p style={{ marginTop: '8px', padding: '12px', background: '#f5f5f5', borderRadius: '4px' }}>
                      {incident.narrative}
                    </p>
                    {incident.confidence && (
                      <Badge text={`Confidence: ${incident.confidence}`} color="blue" />
                    )}
                  </div>
                )}
              </VerticalGroup>
            </Card>
          )}

          {activeTab === 'timeline' && (
            <Card>
              <Card.Heading>Timeline</Card.Heading>
              <VerticalGroup spacing="sm">
                {incident.timeline.map((entry, idx) => (
                  <div key={idx} style={{ padding: '8px', borderLeft: '2px solid #ccc', paddingLeft: '12px' }}>
                    <div><strong>{formatTimestamp(entry.ts)}</strong></div>
                    <div>{entry.event}</div>
                    {entry.description && <div style={{ color: '#666' }}>{entry.description}</div>}
                  </div>
                ))}
              </VerticalGroup>
            </Card>
          )}

          {activeTab === 'evidence' && (
            <Card>
              <Card.Heading>Evidence</Card.Heading>
              <VerticalGroup spacing="sm">
                {incident.evidence.map((ev, idx) => (
                  <div key={idx} style={{ padding: '8px', background: '#f9f9f9', borderRadius: '4px' }}>
                    <div><strong>Reference:</strong> <code>{ev.ref}</code></div>
                    {ev.summary && <div><strong>Summary:</strong> {ev.summary}</div>}
                    {ev.weight && <div><strong>Weight:</strong> {ev.weight}</div>}
                  </div>
                ))}
              </VerticalGroup>
            </Card>
          )}

          {activeTab === 'narrative' && (
            <Card>
              <Card.Heading>AI-Generated Narrative</Card.Heading>
              {incident.narrative ? (
                <div style={{ padding: '12px', background: '#f5f5f5', borderRadius: '4px', whiteSpace: 'pre-wrap' }}>
                  {incident.narrative}
                </div>
              ) : (
                <Alert title="No Narrative" severity="info">
                  AI narrative has not been generated yet. It may be processing asynchronously.
                </Alert>
              )}
            </Card>
          )}

          {activeTab === 'runbooks' && (
            <Card>
              <Card.Heading>Recommended Runbooks</Card.Heading>
              <VerticalGroup spacing="sm">
                {incident.runbook_refs.map((rb, idx) => (
                  <Card key={idx}>
                    <Card.Heading>{rb.title}</Card.Heading>
                    <Card.Meta>
                      <HorizontalGroup>
                        <Badge text={rb.id} color="blue" />
                        {rb.risk && <Badge text={`Risk: ${rb.risk}`} color={rb.risk === 'low' ? 'green' : rb.risk === 'medium' ? 'orange' : 'red'} />}
                      </HorizontalGroup>
                    </Card.Meta>
                  </Card>
                ))}
                {incident.runbook_refs.length === 0 && (
                  <Alert title="No Runbooks" severity="info">
                    No runbooks have been recommended for this incident.
                  </Alert>
                )}
              </VerticalGroup>
            </Card>
          )}
        </TabContent>
      </VerticalGroup>

      {/* Modals */}
      <ConfirmModal
        isOpen={showAckModal}
        title="Acknowledge Incident"
        body={
          <Field label="Comment (optional)">
            <TextArea
              value={comment}
              onChange={(e) => setComment(e.currentTarget.value)}
              placeholder="Add a comment..."
              rows={3}
            />
          </Field>
        }
        confirmText="Acknowledge"
        onConfirm={handleAcknowledge}
        onDismiss={() => setShowAckModal(false)}
      />

      <ConfirmModal
        isOpen={showResolveModal}
        title="Resolve Incident"
        body={
          <Field label="Resolution (optional)">
            <TextArea
              value={comment}
              onChange={(e) => setComment(e.currentTarget.value)}
              placeholder="Describe how this was resolved..."
              rows={3}
            />
          </Field>
        }
        confirmText="Resolve"
        onConfirm={handleResolve}
        onDismiss={() => setShowResolveModal(false)}
      />

      <ConfirmModal
        isOpen={showSuppressModal}
        title="Suppress Incident"
        body={
          <Field label="Reason (optional)">
            <TextArea
              value={comment}
              onChange={(e) => setComment(e.currentTarget.value)}
              placeholder="Why are you suppressing this incident..."
              rows={3}
            />
          </Field>
        }
        confirmText="Suppress"
        confirmVariant="destructive"
        onConfirm={handleSuppress}
        onDismiss={() => setShowSuppressModal(false)}
      />
    </div>
  );
}
