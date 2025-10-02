/**
 * AIOps Operations Console - Main Plugin Module
 */

import React from 'react';
import { AppPlugin } from '@grafana/data';
import { AppRootProps } from '@grafana/data';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Import pages
import { IncidentsPage } from './pages/IncidentsPage';
import { IncidentDetailPage } from './pages/IncidentDetailPage';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { ActionsPage } from './pages/ActionsPage';
import { PolicyPage } from './pages/PolicyPage';

/**
 * Root component for the App Plugin
 */
function AppRoot(props: AppRootProps) {
  const basePath = props.meta.baseUrl;

  return (
    <Router basename={basePath}>
      <Routes>
        <Route path="/" element={<Navigate to="/incidents" replace />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/incidents/:incidentId" element={<IncidentDetailPage />} />
        <Route path="/approvals" element={<ApprovalsPage />} />
        <Route path="/actions" element={<ActionsPage />} />
        <Route path="/policy" element={<PolicyPage />} />
      </Routes>
    </Router>
  );
}

/**
 * Plugin configuration
 */
export const plugin = new AppPlugin<{}>().setRootPage(AppRoot);
