/**
 * Approvals Page - Two-person approval workflow
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
  TextArea,
  Field,
  TabsBar,
  Tab,
  TabContent,
} from '@grafana/ui';
import { apiClient } from '../api/client';
import type { Approval } from '../types';
import { formatTimestamp, formatRelativeTime, getSeverityColor } from '../utils/helpers';

export function ApprovalsPage() {
  const [pendingApprovals, setPendingApprovals] = useState<Approval[]>([]);
  const [myApprovals, setMyApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('pending');
  const [selectedApproval, setSelectedApproval] = useState<Approval | null>(null);
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [comment, setComment] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    loadApprovals();
  }, []);

  const loadApprovals = async () => {
    try {
      setLoading(true);
      setError(null);
      const [pendingResponse, myResponse] = await Promise.all([
        apiClient.getPendingApprovals(),
        apiClient.getMyApprovals(),
      ]);
      setPendingApprovals(pendingResponse.data || []);
      setMyApprovals(myResponse.data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load approvals');
      console.error('Error loading approvals:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!selectedApproval) return;
    try {
      setActionLoading(true);
      await apiClient.approveAction(
        selectedApproval.incident_id,
        selectedApproval.approval_id,
        comment
      );
      setShowApproveModal(false);
      setComment('');
      setSelectedApproval(null);
      await loadApprovals();
    } catch (err: any) {
      setError(err.message || 'Failed to approve action');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedApproval) return;
    try {
      setActionLoading(true);
      await apiClient.rejectAction(
        selectedApproval.incident_id,
        selectedApproval.approval_id,
        comment
      );
      setShowRejectModal(false);
      setComment('');
      setSelectedApproval(null);
      await loadApprovals();
    } catch (err: any) {
      setError(err.message || 'Failed to reject action');
    } finally {
      setActionLoading(false);
    }
  };

  const renderApprovalCard = (approval: Approval) => (
    <Card key={approval.approval_id}>
      <Card.Heading>{approval.action_type.replace(/_/g, ' ')}</Card.Heading>
      <Card.Meta>
        <HorizontalGroup spacing="sm">
          <Badge text={approval.incident_severity} color={getSeverityColor(approval.incident_severity)} />
          <Badge text={approval.incident_type.replace(/_/g, ' ')} color="blue" />
          {approval.requires_two_person && <Badge text="Two-Person Required" color="orange" />}
          <span>{formatRelativeTime(approval.requested_at)}</span>
        </HorizontalGroup>
      </Card.Meta>
      <Card.Description>
        <VerticalGroup spacing="sm">
          <div><strong>Ship:</strong> {approval.ship_id}</div>
          <div><strong>Requested by:</strong> {approval.requested_by}</div>
          <div><strong>Requested at:</strong> {formatTimestamp(approval.requested_at)}</div>
          {approval.requires_two_person && (
            <div>
              <strong>Approvals:</strong> {approval.approvals_count} / {approval.approvals_required}
            </div>
          )}
          {approval.action_details && (
            <div>
              <strong>Action Details:</strong>
              <pre style={{ marginTop: '8px', padding: '8px', background: '#f5f5f5', borderRadius: '4px', fontSize: '12px' }}>
                {JSON.stringify(approval.action_details, null, 2)}
              </pre>
            </div>
          )}
        </VerticalGroup>
      </Card.Description>
      <Card.Actions>
        <Button
          variant="primary"
          onClick={() => {
            setSelectedApproval(approval);
            setShowApproveModal(true);
          }}
          disabled={approval.status !== 'pending'}
        >
          Approve
        </Button>
        <Button
          variant="destructive"
          onClick={() => {
            setSelectedApproval(approval);
            setShowRejectModal(true);
          }}
          disabled={approval.status !== 'pending'}
        >
          Reject
        </Button>
      </Card.Actions>
    </Card>
  );

  return (
    <div style={{ padding: '20px' }}>
      <VerticalGroup spacing="lg">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Approvals</h2>
          <Button icon="sync" onClick={loadApprovals} disabled={loading}>
            Refresh
          </Button>
        </div>

        {error && <Alert title="Error" severity="error">{error}</Alert>}

        <TabsBar>
          <Tab
            label={`Pending (${pendingApprovals.length})`}
            active={activeTab === 'pending'}
            onChangeTab={() => setActiveTab('pending')}
          />
          <Tab
            label={`My Approvals (${myApprovals.length})`}
            active={activeTab === 'mine'}
            onChangeTab={() => setActiveTab('mine')}
          />
        </TabsBar>

        <TabContent>
          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
              <Spinner size="lg" />
            </div>
          ) : (
            <VerticalGroup spacing="md">
              {activeTab === 'pending' && (
                <>
                  {pendingApprovals.length === 0 ? (
                    <Alert title="No Pending Approvals" severity="info">
                      There are no actions awaiting approval at this time.
                    </Alert>
                  ) : (
                    pendingApprovals.map(renderApprovalCard)
                  )}
                </>
              )}

              {activeTab === 'mine' && (
                <>
                  {myApprovals.length === 0 ? (
                    <Alert title="No Approvals" severity="info">
                      You have not submitted any approvals yet.
                    </Alert>
                  ) : (
                    myApprovals.map(renderApprovalCard)
                  )}
                </>
              )}
            </VerticalGroup>
          )}
        </TabContent>
      </VerticalGroup>

      {/* Approve Modal */}
      <ConfirmModal
        isOpen={showApproveModal}
        title="Approve Action"
        body={
          selectedApproval && (
            <VerticalGroup spacing="md">
              <Alert title="Approval Details" severity="info">
                <div>Action: {selectedApproval.action_type}</div>
                <div>Ship: {selectedApproval.ship_id}</div>
                {selectedApproval.requires_two_person && (
                  <div>
                    This action requires two-person approval.
                    Current approvals: {selectedApproval.approvals_count} / {selectedApproval.approvals_required}
                  </div>
                )}
              </Alert>
              <Field label="Comment (optional)">
                <TextArea
                  value={comment}
                  onChange={(e) => setComment(e.currentTarget.value)}
                  placeholder="Add approval comment..."
                  rows={3}
                />
              </Field>
            </VerticalGroup>
          )
        }
        confirmText="Approve"
        onConfirm={handleApprove}
        onDismiss={() => {
          setShowApproveModal(false);
          setComment('');
          setSelectedApproval(null);
        }}
      />

      {/* Reject Modal */}
      <ConfirmModal
        isOpen={showRejectModal}
        title="Reject Action"
        body={
          selectedApproval && (
            <VerticalGroup spacing="md">
              <Alert title="Rejection" severity="warning">
                You are about to reject this action request.
              </Alert>
              <Field label="Reason (required)">
                <TextArea
                  value={comment}
                  onChange={(e) => setComment(e.currentTarget.value)}
                  placeholder="Please provide a reason for rejection..."
                  rows={3}
                />
              </Field>
            </VerticalGroup>
          )
        }
        confirmText="Reject"
        confirmVariant="destructive"
        onConfirm={handleReject}
        onDismiss={() => {
          setShowRejectModal(false);
          setComment('');
          setSelectedApproval(null);
        }}
      />
    </div>
  );
}
