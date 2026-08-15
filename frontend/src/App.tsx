import { Navigate, Route, Routes } from "react-router-dom";

import MainLayout from "./layouts/MainLayout";
import LoginPage from "./pages/auth/LoginPage";
import DashboardPage from "./pages/dashboard/DashboardPage";
import PlaceholderPage from "./pages/PlaceholderPage";
import ProtectedRoute from "./routes/ProtectedRoute";
import DataSourcesPage from "./pages/dataSources/DataSourcesPage";
import ChatPage from "./pages/chat/ChatPage";
import MetadataExplorerPage from "./pages/metadata/MetadataExplorerPage";
import PromptIntelligencePage from "./pages/intelligence/PromptIntelligencePage";
import AiPlaygroundPage from "./pages/playground/AiPlaygroundPage";
import BusinessEntityRegistryPage from "./pages/business-entities/BusinessEntityRegistryPage";
import BusinessRelationshipExplorerPage from "./pages/business-relationships/BusinessRelationshipExplorerPage";
import KnowledgeGraphPage from "./pages/knowledge-graph/KnowledgeGraphPage";
import BusinessCapabilityRegistryPage from "./pages/business-capabilities/BusinessCapabilityRegistryPage";
import ReasoningExplorerPage from "./pages/reasoning/ReasoningExplorerPage";
import SqlCompilerPage from "./pages/sql-compiler/SqlCompilerPage";
import BusinessRuleRegistryPage from "./pages/business-rules/BusinessRuleRegistryPage";
import AskNIBGPTPage from "./pages/ask";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<MainLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />

          <Route
            path="/chat"
            element={<ChatPage />}
          />

          <Route
          path="/ask"
          element={<AskNIBGPTPage />}
        />

          <Route
            path="/reports"
            element={
              <PlaceholderPage
                title="Prompt Reports"
                description="Approved prompt-based Oracle and MySQL reports will be managed here."
              />
            }
          />

          <Route
            path="/documents"
            element={
              <PlaceholderPage
                title="Documents"
                description="Policies, procedures, directives and institutional documents will be managed here."
              />
            }
          />

          <Route
  path="/data-sources"
  element={<DataSourcesPage />}
/>

<Route
  path="/metadata"
  element={<MetadataExplorerPage />}
/>

<Route
  path="/prompt-intelligence"
  element={<PromptIntelligencePage />}
/>
<Route
  path="/ai-playground"
  element={<AiPlaygroundPage />}
/>

<Route
  path="/business-entities"
  element={<BusinessEntityRegistryPage />}
/>

<Route
  path="/business-relationships"
  element={<BusinessRelationshipExplorerPage />}
/>

<Route
  path="/knowledge-graph"
  element={<KnowledgeGraphPage />}
/>

<Route
  path="/business-capabilities"
  element={<BusinessCapabilityRegistryPage />}
/>

<Route
  path="/reasoning-explorer"
  element={<ReasoningExplorerPage />}
/>

<Route
  path="/sql-compiler"
  element={<SqlCompilerPage />}
/>

<Route
  path="/business-rules"
  element={
    <BusinessRuleRegistryPage />
  }
/>

          <Route
            path="/knowledge-base"
            element={
              <PlaceholderPage
                title="Knowledge Base"
                description="Institutional metadata, business definitions and indexed knowledge will be maintained here."
              />
            }
          />

          <Route
            path="/ai-models"
            element={
              <PlaceholderPage
                title="AI Models"
                description="NIB-owned models, training versions and evaluation results will be managed here."
              />
            }
          />

          <Route
            path="/users"
            element={
              <PlaceholderPage
                title="User Management"
                description="Administrators will create, activate and manage NIBGPT users here."
              />
            }
          />

          <Route
            path="/settings"
            element={
              <PlaceholderPage
                title="System Settings"
                description="Platform, security and application settings will be configured here."
              />
            }
          />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default App;