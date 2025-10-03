/**
 * Actions Page - Safe runbook execution
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
  ConfirmModal,
  Field,
  Input,
  Select,
} from '@grafana/ui';
import { apiClient } from '../api/client';
import type { Action, ActionExecution } from '../types';
import { getRiskColor, isOnCooldown, timeUntilAvailable } from '../utils/helpers';

export function ActionsPage() {
  const [actions, setActions] = useState<Action[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAction, setSelectedAction] = useState<Action | null>(null);
  const [showExecuteModal, setShowExecuteModal] = useState(false);
  const [parameters, setParameters] = useState<Record<string, any>>({});
  const [incidentId, setIncidentId] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [execution, setExecution] = useState<ActionExecution | null>(null);
  const [showResultModal, setShowResultModal] = useState(false);

  useEffect(() => {
    loadActions();
  }, []);

  const loadActions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getAvailableActions();
      setActions(response.data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load actions');
      console.error('Error loading actions:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!selectedAction) return;
    try {
      setActionLoading(true);
      const response = await apiClient.executeAction(
        selectedAction.action_id,
        incidentId,
        parameters
      );
      setExecution(response.data || null);
      setShowExecuteModal(false);
      setShowResultModal(true);
      // Reset form
      setParameters({});
      setIncidentId('');
      setSelectedAction(null);
      await loadActions(); // Refresh to update cooldowns
    } catch (err: any) {
      setError(err.message || 'Failed to execute action');
    } finally {
      setActionLoading(false);
    }
  };

  const openExecuteModal = (action: Action) => {
    setSelectedAction(action);
    // Initialize parameters with defaults
    const params: Record<string, any> = {};
    action.parameters?.forEach(param => {
      if (param.default !== undefined) {
        params[param.name] = param.default;
      }
    });
    setParameters(params);
    setShowExecuteModal(true);
  };

  const renderActionCard = (action: Action) => {
    const onCooldown = isOnCooldown(action.last_executed, action.cooldown_sec);

    return (
      <Card key={action.action_id}>
        <Card.Heading>{action.name}</Card.Heading>
        <Card.Meta>
          <HorizontalGroup spacing="sm">
            <Badge text={`Risk: ${action.risk}`} color={getRiskColor(action.risk)} />
            {!action.allowed && <Badge text="Not Allowed" color="red" />}
            {action.requires_approval && <Badge text="Requires Approval" color="orange" />}
            {action.requires_two_person && <Badge text="Two-Person" color="purple" />}
            {onCooldown && (
              <Badge
                text={`Cooldown: ${timeUntilAvailable(action.last_executed!, action.cooldown_sec)}`}
                color="gray"
              />
            )}
          </HorizontalGroup>
        </Card.Meta>
        <Card.Description>
          <p>{action.description}</p>
          {action.parameters && action.parameters.length > 0 && (
            <div style={{ marginTop: '8px' }}>
              <strong>Parameters:</strong>
              <ul style={{ marginLeft: '20px', marginTop: '4px' }}>
                {action.parameters.map(param => (
                  <li key={param.name}>
                    {param.name} ({param.type})
                    {param.required && <span style={{ color: 'red' }}>*</span>}
                    {param.default !== undefined && ` = ${param.default}`}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card.Description>
        <Card.Actions>
          <Button
            variant="primary"
            onClick={() => openExecuteModal(action)}
            disabled={!action.allowed || onCooldown}
          >
            Execute
          </Button>
        </Card.Actions>
      </Card>
    );
  };

  return (
    <div style={{ padding: '20px' }}>
      <VerticalGroup spacing="lg">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Action Center</h2>
          <Button icon="sync" onClick={loadActions} disabled={loading}>
            Refresh
          </Button>
        </div>

        {error && <Alert title="Error" severity="error">{error}</Alert>}

        <Alert title="Safe Actions" severity="info">
          Only pre-approved, low-risk actions can be executed from this console.
          All actions are logged and audited. Cooldown periods are enforced to prevent accidental repeated execution.
        </Alert>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
            <Spinner size="lg" />
          </div>
        ) : (
          <VerticalGroup spacing="md">
            {actions.length === 0 ? (
              <Alert title="No Actions Available" severity="info">
                No actions are currently available. Check policy configuration.
              </Alert>
            ) : (
              actions.map(renderActionCard)
            )}
          </VerticalGroup>
        )}
      </VerticalGroup>

      {/* Execute Modal */}
      <ConfirmModal
        isOpen={showExecuteModal}
        title={`Execute: ${selectedAction?.name}`}
        body={
          selectedAction && (
            <VerticalGroup spacing="md">
              <Alert title="Pre-Execution Checks" severity="info">
                <div><strong>Action:</strong> {selectedAction.name}</div>
                <div><strong>Risk Level:</strong> {selectedAction.risk}</div>
                <div><strong>Description:</strong> {selectedAction.description}</div>
              </Alert>

              <Field label="Incident ID (optional)">
                <Input
                  value={incidentId}
                  onChange={(e) => setIncidentId(e.currentTarget.value)}
                  placeholder="Link to incident..."
                />
              </Field>

              {selectedAction.parameters && selectedAction.parameters.length > 0 && (
                <>
                  <h4>Parameters</h4>
                  {selectedAction.parameters.map(param => (
                    <Field
                      key={param.name}
                      label={`${param.name}${param.required ? ' *' : ''}`}
                      description={`Type: ${param.type}`}
                    >
                      {param.type === 'string' || param.type === 'number' ? (
                        <Input
                          type={param.type === 'number' ? 'number' : 'text'}
                          value={parameters[param.name] || ''}
                          onChange={(e) =>
                            setParameters({
                              ...parameters,
                              [param.name]: param.type === 'number' 
                                ? parseFloat(e.currentTarget.value)
                                : e.currentTarget.value,
                            })
                          }
                          placeholder={param.default?.toString() || ''}
                        />
                      ) : param.type === 'boolean' ? (
                        <Select
                          options={[
                            { label: 'True', value: true },
                            { label: 'False', value: false },
                          ]}
                          value={parameters[param.name]}
                          onChange={(v) =>
                            setParameters({ ...parameters, [param.name]: v.value })
                          }
                        />
                      ) : (
                        <Input
                          value={parameters[param.name] || ''}
                          onChange={(e) =>
                            setParameters({ ...parameters, [param.name]: e.currentTarget.value })
                          }
                        />
                      )}
                    </Field>
                  ))}
                </>
              )}

              <Alert title="Confirmation" severity="warning">
                Are you sure you want to execute this action? All executions are audited and logged.
              </Alert>
            </VerticalGroup>
          )
        }
        confirmText="Execute"
        confirmVariant="primary"
        onConfirm={handleExecute}
        onDismiss={() => {
          setShowExecuteModal(false);
          setParameters({});
          setIncidentId('');
          setSelectedAction(null);
        }}
      />

      {/* Result Modal */}
      <ConfirmModal
        isOpen={showResultModal}
        title="Execution Result"
        body={
          execution && (
            <VerticalGroup spacing="md">
              <Alert
                title={execution.status === 'success' ? 'Success' : execution.status === 'failed' ? 'Failed' : 'Running'}
                severity={execution.status === 'success' ? 'success' : execution.status === 'failed' ? 'error' : 'info'}
              >
                Execution ID: {execution.execution_id}
              </Alert>

              {execution.result && (
                <>
                  {execution.result.pre_checks && (
                    <div>
                      <strong>Pre-Checks:</strong>
                      <pre style={{ marginTop: '8px', padding: '8px', background: '#f5f5f5', borderRadius: '4px', fontSize: '12px' }}>
                        {JSON.stringify(execution.result.pre_checks, null, 2)}
                      </pre>
                    </div>
                  )}

                  {execution.result.output && (
                    <div>
                      <strong>Output:</strong>
                      <pre style={{ marginTop: '8px', padding: '8px', background: '#f5f5f5', borderRadius: '4px', fontSize: '12px' }}>
                        {execution.result.output}
                      </pre>
                    </div>
                  )}

                  {execution.result.post_checks && (
                    <div>
                      <strong>Post-Checks:</strong>
                      <pre style={{ marginTop: '8px', padding: '8px', background: '#f5f5f5', borderRadius: '4px', fontSize: '12px' }}>
                        {JSON.stringify(execution.result.post_checks, null, 2)}
                      </pre>
                    </div>
                  )}

                  {execution.result.error && (
                    <Alert title="Error" severity="error">
                      {execution.result.error}
                    </Alert>
                  )}
                </>
              )}
            </VerticalGroup>
          )
        }
        confirmText="Close"
        onConfirm={() => {
          setShowResultModal(false);
          setExecution(null);
        }}
        onDismiss={() => {
          setShowResultModal(false);
          setExecution(null);
        }}
      />
    </div>
  );
}
